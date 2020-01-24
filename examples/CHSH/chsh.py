import math

from components.host import Host
from components.network import Network
from components.logger import Logger
from backends.projectq_backend import ProjectQBackend
import random

from objects.qubit import Qubit

Logger.DISABLED = True

PLAYS = 10


def alice_quantum(alice_host, referee_id, bob_id):
    for i in range(PLAYS):
        referee_message = alice_host.get_message_w_seq_num(referee_id, i, wait=5)
        x = int(referee_message.content)
        epr = alice_host.get_epr(bob_id)

        if x == 0:
            res = epr.measure()
            print('Alice sent %d' % res)
            alice_host.send_classical(referee_id, str(res))
        else:
            epr.H()
            res = epr.measure()
            print('Alice sent %d' % res)
            alice_host.send_classical(referee_id, str(res))


def bob_quantum(bob_host, referee_id, alice_id):
    for i in range(PLAYS):
        referee_message = bob_host.get_message_w_seq_num(referee_id, i, wait=5)
        y = int(referee_message.content)
        epr = bob_host.get_epr(alice_id)

        if y == 0:
            epr.ry(-2.0 * math.pi / 8.0)
            res = epr.measure()
            print('Bob sent %d' % res)
            bob_host.send_classical(referee_id, str(res))
        else:
            epr.ry(2.0 * math.pi / 8.0)
            res = epr.measure()
            print('Bob sent %d' % res)
            bob_host.send_classical(referee_id, str(res))


def referee(ref, alice_id, bob_id):
    # Here we write the protocol code for a host.
    wins = 0
    for i in range(PLAYS):
        x = random.choice([0, 1])
        ref.send_classical(alice_id, str(x))
        y = random.choice([0, 1])
        ref.send_classical(bob_id, str(y))

        alice_response = ref.get_message_w_seq_num(alice_id, i, wait=5)
        bob_response = ref.get_message_w_seq_num(bob_id, i, wait=5)

        a = int(alice_response.content)
        b = int(bob_response.content)

        print('X, Y, A, B --- %d, %d, %d, %d' % (x, y, a, b))
        if x & y == a ^ b:
            print('Winners!')
            wins += 1
        else:
            print('Losers!')
    print("Win ratio: %f" % (float(wins) / PLAYS))


def alice_classical(alice_host, referee_id):
    # Here we write the protocol code for a host.
    for i in range(PLAYS):
        _ = alice_host.get_message_w_seq_num(referee_id, i, wait=5)
        alice_host.send_classical(referee_id, "0")


def bob_classical(bob_host, referee_id):
    # Here we write the protocol code for another host.
    for i in range(PLAYS):
        _ = bob_host.get_message_w_seq_num(referee_id, i, wait=5)
        bob_host.send_classical(referee_id, "0")
        pass


def main():
    network = Network.get_instance()
    backend = ProjectQBackend()
    nodes = ['A', 'B', 'C']
    network.start(nodes, backend)
    network.delay = 0
    #
    host_A = Host('A', backend)
    host_A.add_c_connection('C')
    host_A.start()

    host_B = Host('B', backend)
    host_B.add_c_connection('C')
    host_B.start()

    host_C = Host('C', backend)
    host_C.add_c_connection('A')
    host_C.add_c_connection('B')
    host_C.start()

    network.add_host(host_C)
    #
    # Generate entanglement
    host_A.add_connection('B')
    host_B.add_connection('A')
    #
    network.add_host(host_A)
    network.add_host(host_B)

    for i in range(PLAYS):
        host_A.send_epr('B', await_ack=True)

    # Remove the connection from Alice and Bob
    host_A.remove_connection('B')
    host_B.remove_connection('A')
    network.update_host(host_A)
    network.update_host(host_B)

    host_C.run_protocol(referee, (host_A.host_id, host_B.host_id))

    # Play the game classically
    # host_A.run_protocol(alice_classical, (host_C.host_id,))
    # host_B.run_protocol(bob_classical, (host_C.host_id,))

    # Play the game quantumly
    host_A.run_protocol(alice_quantum, (host_C.host_id, host_B.host_id))
    host_B.run_protocol(bob_quantum, (host_C.host_id, host_A.host_id))


if __name__ == '__main__':
    main()
