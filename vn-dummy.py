import sys
import socket
import struct
import select
import time
import heapq

def main():
    if len(sys.argv) != 5:
        print(f"Usage: python {sys.argv[0]} <on_ip> <on_port> <own_ip> <own_udp_port>")
        sys.exit(1)
        
    on_ip=sys.argv[1]
    on_port=int(sys.argv[2])
    vn_ip=sys.argv[3]
    vn_udp_port=int(sys.argv[4])
    
    try:
        udp_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    except Exception as e:
        print(f"udp_socket failed:{e}")
    udp_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        udp_socket.bind((vn_ip,vn_udp_port))
    except Exception as e:
        print(f"couldn't bind udp_socket:{e}")
        
        
        
    try:
        tcp_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except Exception as e:
        print(f"tcp_socket failed:{e}")
    tcp_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        tcp_socket.connect((on_ip,on_port))
    except Exception as e:
        print(f"couldn't connect tcp_socket:{e}")
        
    
    try:
        ip_bytes=socket.inet_aton(vn_ip)
        msg=ip_bytes+ vn_udp_port.to_bytes(2, 'big')
        tcp_socket.sendall(msg)
    except Exception as e:
        print(f"Error sending CONNECT message: {e}")
        tcp_socket.close()
        sys.exit(1)
        

    origin_id=None
    seq_num=0
    neighbors={}

    ls_info={}


    def print_ls_info(origin_id, ls_info):
        if origin_id is None:
            return

        all_nodes = set([origin_id])
        for node, info in ls_info.items():
            all_nodes.add(node)
            for dest in info['costs'].keys():
                all_nodes.add(dest)

        #redundant
        for node in neighbors.keys():
            all_nodes.add(node)

        nodes = sorted(list(all_nodes))
        if len(nodes)<=1:
            return

        directed_graph = {node: {} for node in nodes}

        for node, data in neighbors.items():
            if data['cost']>0 and node != origin_id:
                directed_graph[origin_id][node] = data['cost']

        for node, info in ls_info.items():
            for dest, cost in info['costs'].items():
                if cost>0:
                    directed_graph[node][dest] = cost

        graph = {node: {} for node in nodes}
        for u in nodes:
            for v, cost in directed_graph[u].items():
                #did v also send about u?
                if u in directed_graph.get(v, {}):
                    graph[u][v] = cost
                    graph[v][u] = cost

        #dijskstra
        all_distances = {}
        for start_node in nodes:
            distances = {n: float('inf') for n in nodes}
            distances[start_node] = 0
            pq = [(0, start_node)]
            visited = set()

            while pq:
                current_dist, u = heapq.heappop(pq)
                if u in visited:
                    continue
                visited.add(u)

                if u in graph:
                    for v, weight in graph[u].items():
                        if current_dist + weight < distances[v]:
                            distances[v] = current_dist + weight
                            heapq.heappush(pq, (distances[v], v))
            all_distances[start_node] = distances

        print(f"Current Link State Information at node {origin_id}:")
        for i in range(len(nodes)-1):
            u = nodes[i]
            target_nodes = nodes[i+1:]
            if not target_nodes:
                continue
                
            print(f"# Costs from {u} to {', '.join(target_nodes)}")
            
            cost_values = []
            for v in target_nodes:
                d = all_distances[u][v]
                if d == float('inf') or d < 0:
                    cost_values.append("-1")
                else:
                    cost_values.append(str(d))

            space = "\t" * i
            print(space + "\t".join(cost_values))

        print()
        sys.stdout.flush()
        
    def lsp_seq(seq_num):
        if not origin_id:
            return seq_num
        
        seq_num += 1
        valid_neighbors = {k: v for k, v in neighbors.items() if v['cost'] > 0 and k != origin_id}
        local_costs = {nei_id: nei_data['cost'] for nei_id, nei_data in valid_neighbors.items()}
        ls_info[origin_id] = {
            'seq': seq_num,
            'costs': local_costs
        }
        
        packet = origin_id.encode('ascii')
        packet += seq_num.to_bytes(4, 'big')
        packet += len(valid_neighbors).to_bytes(2, 'big')
        
        for nei_id, nei_data in valid_neighbors.items():
                    packet += nei_id.encode('ascii')
                    packet +=nei_data['cost'].to_bytes(2, 'big', signed=True)
            
        for nei_id, nei_data in valid_neighbors.items():
            dest_addr = (nei_data['ip'], nei_data['udp_port'])
            udp_socket.sendto(packet, dest_addr)

        print_ls_info(origin_id, ls_info)
        print(f"Sent LSP (Seq: {seq_num}) to neighbors: {list(valid_neighbors.keys())}")
        print()
        sys.stdout.flush()
        return seq_num
    
    inputs=[tcp_socket,udp_socket]
    period=20.0
    last_period_time=time.time()
    try:
        while True:
            
            current_time=time.time()
            elapsed=current_time-last_period_time
            timeout=max(0.1,period-elapsed)
            
            incoming_msgs, _, _=select.select(inputs,[],[],timeout)
            
            if time.time()-last_period_time >= period:
                if origin_id and neighbors:
                    print()
                    print(f"--------------- printing ls_info and sending lsp ---------------")
                    seq_num=lsp_seq(seq_num)
                last_period_time=time.time()
                
            for s in incoming_msgs:
                if s is tcp_socket:
                    data=tcp_socket.recv(1024)
                    if not data:
                        print(f"empty data from on")
                        return
                    tuple_size=11
                    num_neighbors=len(data) // tuple_size
                    neighbors_info=[]
                    new_neighbors={}
                    
                    for i in range(num_neighbors):
                        offset= i*tuple_size
                        d=data[offset:offset+tuple_size]
                        if len(d)<tuple_size:
                            break
                        
                        nodeId=d[0:1].decode('ascii')
                        node_ip=socket.inet_ntoa(d[1:5])
                        node_port=int.from_bytes(d[5:7],'big')
                        node_cost=int.from_bytes(d[7:11],'big',signed=True)
                        
                        if node_cost==0:
                            origin_id=nodeId
                            
                        new_neighbors[nodeId]={
                            'ip':node_ip,
                            'udp_port':node_port,
                            'cost':node_cost
                        }
                        neighbors_info.append(f"{nodeId}={node_cost}")
                    neighbors=new_neighbors
                    print()
                    print(f"########## message from ON ##########")
                    print(f"msg received from on: {', '.join(neighbors_info)}")
                    print()
                    sys.stdout.flush()
                    seq_num=lsp_seq(seq_num)
                    
                elif s is udp_socket:
                    data, sender_addr = udp_socket.recvfrom(1024)
                    if len(data) >= 7:
                        origin_bytes, seq_n, num_n = struct.unpack('!cIH', data[:7])
                        origin = origin_bytes.decode('ascii')
                        
                        relayer = "..."
                        for k, v in neighbors.items():
                            if (v['ip'], v['udp_port']) == sender_addr:
                                relayer = k
                                break

                        costs_received = {}
                        offset = 7
                        for _ in range(num_n):
                            if offset + 3 > len(data):
                                break
                            id1 = data[offset:offset+1].decode('ascii')
                            cost1 = int.from_bytes(data[offset+1:offset+3], 'big', signed=True)
                            costs_received[id1] = cost1
                            offset+=3
                            
                        if origin not in ls_info or seq_n > ls_info[origin]['seq']:
                            ls_info[origin] = {
                                'seq': seq_n,
                                'costs': costs_received
                            }
                            
                            costs_str = [f"{k}={v}" for k, v in costs_received.items()]
                            print(f"Received info about Node {origin} (relayed by neighbor {relayer}), seq:{seq_n}, costs: {', '.join(costs_str)}")
                            
                            print_ls_info(origin_id, ls_info)
                            
                            valid_neighbors = {k: v for k, v in neighbors.items() if v['cost'] > 0 and k != origin_id}
                            for nei_id, nei_data in valid_neighbors.items():
                                dest_addr = (nei_data['ip'], nei_data['udp_port'])
                                if dest_addr != sender_addr and nei_id != origin:
                                    udp_socket.sendto(data, dest_addr)
                        else:
                            print(f"Received old or duplicate LSP originating from {origin} (via {relayer}), ignoring.")

                        sys.stdout.flush()

    except KeyboardInterrupt:
        print(f"shutdowm vn node")
    finally:
        tcp_socket.close()
        udp_socket.close()
if __name__=='__main__':
    main()
                    
                    
    
        
        
                
        
        
  
    