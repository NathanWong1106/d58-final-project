# def launch():
#   print("hello!")
  
# def _handle_PacketIn(event):
#     packet = event.parsed
#     print(f"PacketIn received: src={packet.src}, dst={packet.dst}")

from pox.core import core

def launch():
    print("✅ Load balancer module loaded!")
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    
def _handle_PacketIn(event):
    packet = event.parsed
    print("[LOAD BALANCER] Packet in switch {event.dpid}: {packet}")