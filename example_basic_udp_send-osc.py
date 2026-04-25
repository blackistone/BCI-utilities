from __future__ import annotations
import socket
from typing import Dict, Optional

import ioiocore as ioc
import numpy as np
import struct

from gpype.common.constants import Constants
from gpype.backend.core.i_node import INode


class UDPSenderOSC(INode):
    """OSC sender for real-time data transmission over network.

    This class implements a UDP-based data sender that transmits incoming
    data blocks immediately during step() execution. The sender uses direct
    UDP transmission without additional threading to maintain real-time
    performance and minimize latency.

    The data is automatically serialized as float64 numpy arrays before
    transmission, ensuring consistent data format across the network. Each
    step() call results in one UDP packet being sent.

    Features:
    - Direct UDP transmission without threading overhead
    - Automatic float64 serialization for network compatibility
    - Configurable IP address and port settings
    - Real-time safe operation with minimal latency

    Attributes:
        DEFAULT_IP: Default target IP address (localhost)
        DEFAULT_PORT: Default target port number
        _socket: UDP socket for data transmission
        _target: Target address tuple (ip, port)

    Note:
        Data is serialized as float64 numpy array before sending. One UDP
        packet is sent per step() call. The receiving end is responsible
        for proper deserialization of the binary data.
    """

    DEFAULT_IP = "127.0.0.1"
    DEFAULT_PORT = 56000

    class Configuration(ioc.INode.Configuration):
        """Configuration class for UDPSender parameters."""

        class Keys(ioc.INode.Configuration.Keys):
            """Configuration keys for UDP sender settings."""
            IP = "ip"
            PORT = "port"

    def __init__(self,
                 ip: Optional[str] = None,
                 port: Optional[int] = None,
                 **kwargs):
        """Initialize the UDP sender with target address and port.

        Args:
            ip: Target IP address for UDP transmission. If None, uses
                DEFAULT_IP (localhost). Can be any valid IPv4 address.
            port: Target port number for UDP transmission. If None, uses
                DEFAULT_PORT. Must be a valid port number (1-65535).
            **kwargs: Additional arguments passed to parent INode class.
        """
        # Use default values if not specified
        if ip is None:
            ip = UDPSenderOSC.DEFAULT_IP
        if port is None:
            port = UDPSenderOSC.DEFAULT_PORT

        # Initialize parent INode with configuration
        INode.__init__(self,
                       ip=ip,
                       port=port,
                       **kwargs)

        # Initialize networking components
        self._socket = None  # UDP socket (created on start)
        self._target = (ip, port)  # Target address tuple

    def start(self):
        """Start the UDP sender and initialize socket connection.

        Creates a UDP socket and configures the target address from
        the current configuration. The socket is ready for immediate
        data transmission after this method completes.

        Raises:
            OSError: If socket creation fails or address is invalid.

        Note:
            The target address is read from configuration to support
            dynamic address changes between start/stop cycles.
        """
        # Create UDP socket for data transmission
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Update target address from current configuration
        self._target = (self.config[self.Configuration.Keys.IP],
                        self.config[self.Configuration.Keys.PORT])

        # Call parent start method
        super().start()

    def stop(self):
        """Stop the UDP sender and clean up socket resources.

        Properly closes the UDP socket if it exists and resets the
        socket reference to None. This ensures clean resource cleanup
        and prevents potential network resource leaks.

        Note:
            Socket closure is handled gracefully - if the socket is
            already closed or None, no error is raised.
        """
        # Close socket and clean up resources
        if self._socket:
            self._socket.close()
            self._socket = None

        # Call parent stop method
        super().stop()

    def setup(self,
              data: Dict[str, np.ndarray],
              port_context_in: Dict[str, dict]) -> Dict[str, dict]:
        """Setup method called before processing begins.

        This method is called during pipeline initialization but requires
        no specific setup for UDP transmission since all configuration
        is handled during start().

        Args:
            data: Dictionary of input data arrays from connected ports.
            port_context_in: Context information from input ports.

        Returns:
            Empty dictionary as this is a sink node with no output context.

        Note:
            UDP transmission requires no data-dependent configuration,
            so this method simply returns an empty context dictionary.
        """
        # No setup required for UDP transmission
        return {}

    def step(self, data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Process and transmit data via UDP.

        Retrieves data from the default input port, converts it to float64
        format, serializes it to bytes, and transmits it via UDP to the
        configured target address.

        Args:
            data: Dictionary containing input data arrays. Uses the default
                input port to retrieve data for transmission.

        Returns:
            Empty dictionary as this is a sink node with no output data.

        Note:
            Data is automatically converted to float64 format before
            serialization to ensure consistent network representation.
            Each call results in exactly one UDP packet transmission.
        """
        # Get data from default input port
        d = data[Constants.Defaults.PORT_IN]

        # Transmit data if socket is available
        if self._socket:

            # Ensure float32 (OSC uses 32-bit floats)
            d_float = d.astype(np.float32).flatten()
            num_values = len(d_float)

            # --- Encode address pattern ---
            address = b'/eeg/'
            # null-pad to multiple of 4 bytes
            address += b'\0' * ((4 - (len(address) % 4)) % 4)

            # --- Encode type tag string ---
            type_tags = b',' + b'f' * num_values
            type_tags += b'\0' * ((4 - (len(type_tags) % 4)) % 4)

            # --- Encode float arguments ---
            args = b''.join(struct.pack('>f', v) for v in d_float)  # big-endian float32

            # Combine all into final OSC packet
            osc_packet = address + type_tags + args

            # Send UDP packet
            self._socket.sendto(osc_packet, self._target)

        # No output data for sink nodes
        return {}


"""
Basic UDP Send Example - Network Data Transmission via UDP Protocol

This example demonstrates how to stream data over IP networks using the UDP
(User Datagram Protocol) for real-time BCI data transmission. UDP provides
low-latency, connectionless communication ideal for streaming applications
where speed is more important than guaranteed delivery.

What this example shows:
- Generating synthetic 8-channel EEG-like signals with noise
- Capturing keyboard events as experimental markers
- Combining signal and event data using Router
- Streaming combined data over UDP network protocol
- Headless operation (no GUI) for dedicated streaming servers

Expected behavior:
When you run this example:
- UDP packets are sent to the configured network destination
- Data includes 8 signal channels + 1 event channel (9 total)
- Keyboard events are transmitted as numerical markers
- Console shows "Pipeline is running. Press enter to stop."
- Network clients can receive the UDP stream for analysis

Network streaming details:
- Protocol: UDP (User Datagram Protocol)
- Port: Configurable in UDPSender
- Data format: Binary packed multi-channel samples
- Packet rate: 250 Hz (one packet per sample frame)
- Destination: Broadcast or specific IP address

Real-world applications:
- Low-latency BCI control systems
- Real-time signal monitoring across networks
- Distributed processing (send to analysis computers)
- Integration with custom analysis software
- Multi-computer BCI setups
- Remote data logging and backup systems

UDP vs other protocols:
- UDP: Fast, low-latency, no connection overhead (used here)
- TCP: Reliable but higher latency (use for file transfer)
- LSL: Specialized for neuroscience (use for research integration)
- WebSockets: Browser-based applications

Network configuration:
- Sender: This g.Pype application (data source)
- Receiver: Custom application or example_basic_udp_receive.py
- Firewall: May need to allow UDP traffic on specified port
- Local network: Works on same subnet by default

Usage:
    1. Configure network settings in UDPSender if needed
    2. Run: python example_basic_udp_send.py
    3. Use example_basic_udp_receive.py or custom client to receive
    4. Press arrow keys to send event markers over network
    5. Press Enter in console to stop streaming

Note:
    UDP is ideal for real-time applications where occasional packet loss
    is acceptable in exchange for minimal latency and overhead.
"""
import gpype as gp

fs = 250  # Sampling frequency in Hz

if __name__ == "__main__":
    # Create processing pipeline (no GUI needed for UDP streaming)
    p = gp.Pipeline()

    # Generate synthetic 8-channel EEG-like signals
    source = gp.Generator(
        sampling_rate=fs,
        channel_count=8,  # 8 EEG channels
        signal_frequency=10,  # 10 Hz alpha rhythm
        signal_amplitude=10,  # Signal strength
        signal_shape="sine",  # Clean sine waves
        noise_amplitude=10,
    )  # Background noise

    # Capture keyboard input as event markers
    keyboard = gp.Keyboard()  # Arrow keys -> event codes

    # Combine signal data (8 channels) + keyboard events (1 channel)
    router = gp.Router(input_channels=[gp.Router.ALL, gp.Router.ALL])

    # UDP sender for low-latency network streaming
    sender = UDPSenderOSC()  # Streams to configured UDP destination

    # Connect processing chain: signals + events -> UDP network stream
    p.connect(source, router["in1"])  # Signal data -> Router input 1
    p.connect(keyboard, router["in2"])  # Event data -> Router input 2
    p.connect(router, sender)  # Combined data -> UDP stream

    # Start headless UDP streaming operation
    p.start()  # Begin UDP data transmission
    input("Pipeline is running. Press enter to stop.")  # Wait for user
    p.stop()  # Stop streaming and cleanup
