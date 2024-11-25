Computer is connected to iPhone Hotspot
rx_13 (wlp5s0) is in monitor mode
rx_11 (wlp3s0) is connected to the AP

-----------------

AP is being pinged every 0.1sec

Both NICs are arranged in a ULA configuration -- two antennas are attached 
to each. 

Antennas are spaced 3.5cm apart (from the bracket that came with the antennas)

Facing the Antenna Array from the labeled side:
(i.e. the side that we're moving the AP around)

  <3.5cm>
 (3)    (2)     (1)     (0)
 *-------*-------*-------*
AUX    MAIN     MAIN    AUX
(NIC1) (NIC1)   (NIC2) (NIC2)
(mon)  (mon)    (conn) (conn)

NIC1 = wlp5s0 = rx_13
NIC2 = wlp3s0 = rx_11

-----------------------------------
at-boresight:
- Phone placed as close to array boresight as possible

bit-off-boresight:
- Phone placed a little off boresight
- From Array POV, where 90 degrees is boresight & 0 degrees is directly to the right,
  phone is placed roughly 90-15 degrees.

moving-around:
- Phone moves around, and sticks around in a single spot for a bit before moving to another position.

