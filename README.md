UDP-Sender-OSC.py - To be incorporated into the gPype library by g.tec in the directory as their original UDP sender. This can then be run in the manner of their sample UDP send file by an update to the referenced library.

The puredata files take in the BCI-Core 8 data from OSC as per the above sender and creates data clusters from frequency analysis -> 2D PCA -> Kmeans clusters. The latest cluster is sent via OSC for use in creative software packages or coding.

udp-sender-osc.py is a kinda replacement for udp-sender from the gpype library

example-basic-udp-send-osc.py is the udp example and sender lib file combined to just run without configuring anything extra.

port 56000 is the default osc for the library.
