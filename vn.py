import sys
import socket
import struct
import select
import time

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
        tcp_socket.bind((on_ip,on_port))
    except Exception as e:
        print(f"couldn't bind tcp_socket:{e}")
        
    
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
    
    def lsp_seq(seq_num):
        if not origin_id:
            return seq_num
        
        seq_num+=1
        valid_neighbors={k: v for k, v in neighbors.items() if v['cost']>0 and k != origin_id}
        
        packet = origin_id.encode('ascii')
        packet += seq_num.to_bytes(4, 'big')
        packet += len(valid_neighbors).to_bytes(2,'big')
        
        for nei_id, nei_data in valid_neighbors.items():
            packet += nei_id.encode('ascii')
            packet +=nei_data['cost'].to_bytes(2, 'big', signed=True)
            
        for nei_id, nei_data in valid_neighbors.items():
            dest_addr={nei_data['ip'],nei_data['udp_port']}
            udp_socket.sendto(packet,dest_addr)
            
        print(f"Sent LSP (Seq: {seq_num}) to neighbors: {list(valid_neighbors.keys())}")
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
                    print(f"sending periodic lsp")
                    seq_num=lsp_seq(seq_num)
                last_period_time=time.time()
                
            for s in incoming_msgs:
                if s in tcp_socket:
                    data=tcp_socket.rev(1024)
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
                    print(f"msg received from on")
                    sys.stdout.flush()
                    seq_num=lsp_seq(seq_num)
                    
                elif s is udp_socket:
                    data,sender=udp_socket.recv(1024)
                    if len(data)>= 7:
                        origin_bytes,r_seq,num_n=struct.unpack('!cIH',data[:7])
                        origin=origin_bytes.decode('ascii')
                        print(f"received lsp from node {origin},seq:{r_seq},neighbors:{num_n}")
                        sys.stdout.flush()
    except KeyboardInterrupt:
        print(f"shutdowm vn node")
    finally:
        tcp_socket.close()
        udp_socket.close()
if __name__=='__main__':
    main()
                    
                    
    
        
        
                
        
        
  
    