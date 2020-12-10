import networkx as nx
import matplotlib.pyplot as plt
import time
import random

from qunetsim.objects import Qubit, RoutingPacket, Logger, DaemonThread
from queue import Queue
from qunetsim.utils.constants import Constants
from inspect import signature
from qunetsim.backends.emulated_backend import EmulationBackend


# Network singleton
class EmulatedNetwork:
    """ An interface to the real network over the quantum networking card. """
    __instance = None

    @staticmethod
    def get_instance():
        if EmulatedNetwork.__instance is None:
            EmulatedNetwork()
        return EmulatedNetwork.__instance

    def __init__(self):
        if EmulatedNetwork.__instance is None:
            EmulatedNetwork.__instance = self
            self.ARP = {}
            self._use_hop_by_hop = True
            self._packet_queue = Queue()
            self._stop_thread = False
            self._use_ent_swap = False
            self._queue_processor_thread = None
            self._backend = None
        else:
            raise Exception('this is a singleton class')

    def add_host(self, hosts):
        """
        Adds all hosts to a list.

        Args:
            hosts (list): The hosts to be added to the network.
        """
        for host in hosts:
            self.add_host(host)

    def _process_queue(self):
        """
        Runs a thread for processing the packets in the packet queue.

        These packages are then send to the networking card.
        """
        while True:

            packet = self._packet_queue.get()

            if not packet:
                # Stop the network
                self._stop_thread = True
                break

            self._backend.send_packet_to_network(packet)

    def send(self, packet):
        """
        Puts the packet to the packet queue of the network.

        Args:
            packet (Packet): Packet to be sent
        """

        self._packet_queue.put(packet)

    def stop(self, stop_hosts=False):
        """
        Stops the network.
        """

        Logger.get_instance().log("Network stopped")
        try:
            if stop_hosts:
                for host in self.ARP:
                    self.ARP[host].stop(release_qubits=True)

            self.send(None)  # Send None to queue to stop the queue
            if self._backend is not None:
                self._backend.stop()
        except Exception as e:
            Logger.get_instance().error(e)

    def start(self, nodes=None):
        """
        Starts the network.

        """
        self._backend = EmulationBackend()
        if nodes is not None:
            self._backend.start(nodes=nodes)
        self._queue_processor_thread = DaemonThread(target=self._process_queue)
