# -*- coding: utf-8 -*-
"""
Created on Mon Jun  7 14:15:32 2021

@author: hp
"""
import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
import threading
import time


# We will use Global variables - Since we are using only OOPS
# ===============GLOBAL VARIABLES==============================================
nodes = []
stop_threads = False
last_task = ""
# =============================================================================

class Mempool:
    def __init__(self):
        self.transactions = []
        
    def add_transaction(self, amount, sender, receiver):
        new_transaction = Transaction(amount, sender, receiver)
        self.transactions.append(new_transaction)
    
    # Only UTXOs accepted in mempool
    def update_mempool(self):
        self.transactions = [x for x in self.transactions if x.state!='UTXO']
    
    def get_mempool(self):
        return [x.get_transaction() for x in self.transactions]
    
# ===============GLOBAL VARIABLES==============================================
mempool = Mempool()
# =============================================================================

class Transaction:
    def __init__(self, amount, sender, receiver, state = 'UTXO'):
        self.id = str(uuid4()).replace('-', '')
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.state = state
    
    def get_transaction(self):
        return {"id": self.id, 
                "sender": self.sender, 
                "receiver": self.receiver,
                "amount": self.amount,
                "state": self.state}
        
class Block:
    def __init__(self, index, proof, previous_hash, t_max = 0):
        self.index = index
        self.timestamp = str(datetime.datetime.now())
        self.proof = proof
        self.previous_hash = previous_hash
        self.transactions = mempool.transactions[:t_max]
    
    def get_block(self):
        transactions = [x.get_transaction() for x in self.transactions]
        return {"index": self.index, 
                "timestamp": self.timestamp,
                "proof": self.proof, 
                "previous_hash": self.previous_hash,
                "transactions": transactions}

        

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_block(proof = 1, previous_hash = '0')
            
    def create_block(self, proof, previous_hash, t_max = 0):
        block = Block(len(self.chain) + 1, proof, previous_hash, t_max = t_max)
        self.chain.append(block)
        return block
    
    def get_previous_block(self):
        return self.chain[-1]
    
    def hash(self, block):
        block = block.get_block()
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def get_blockchain(self):
        response = [x.get_block() for x in self.chain]
        return response
    

#Node will have its own copy of blockchain, mempool, other connected nodes
class Node:
    def __init__(self):
        self.address = str(uuid4()).replace('-', '')
        self.nodes = nodes 
        self.blockchain = Blockchain()#self.get_blockchain()
        self.wallet_amount = 0#self.get_wallet_amount()
    
    def get_node(self):
        
        response = {"address": self.address,
                    "blockchain": self.blockchain.get_blockchain(),
                    "wallet_amount": self.wallet_amount}
        return response
    
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            global last_task
            global stop_threads
            # print("Task assigned to thread: {}".format(threading.current_thread().name))
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
                stop_threads = True
                last_task = threading.current_thread().name
                continue
            else:
                new_proof += 1
            if stop_threads:
                return
        print(new_proof)
        return new_proof
    
    def mine_block(self, t_max):
        print("Task assigned to thread: {}".format(threading.current_thread().name))
        previous_block = self.blockchain.get_previous_block()
        previous_proof = previous_block.proof
        proof = self.proof_of_work(previous_proof)
        previous_hash = self.blockchain.hash(previous_block)
        block = self.blockchain.create_block(proof, previous_hash, t_max)
        return block
        
        
        
        
class Utility:
    def get_mine_transactions(self):
        # take into account a maximum of 5 transactions
        t_max = 5 if len(mempool)>5 else len(mempool)
        transactions = [mempool[x] for x in range(t_max)]
        return transactions
            
# =============================================================================
# To do: Nodes
#     1. Add Nodes 
#     2. Remove Nodes
#     3. Connect all nodes with each other (Each node is a Node object)
# =============================================================================

# =============================================================================
# To do: Mempool
#   1. Add transactions to mempool
#   2. Update mempool for when transaction will be mined
# =============================================================================

    
#------------------------------- Web App --------------------------------------

# Creating a Web App
app = Flask(__name__)

# Getting the full Blockchain
@app.route('/', methods = ['GET'])
def hello():
    return "Hello", 200

# 1. Nodes ====================================================================

# Add a node and get all nodes=================================================
@app.route('/node', methods = ['POST', 'GET'])
def addNode():
    global nodes
    if request.method == 'POST': 
        new_node = Node()
        nodes.append(new_node)
        response = {'Total Nodes': len(nodes), 
                    'Message': "Node has been added"}
        return jsonify(response), 201
    
    if request.method == 'GET':
        nodes_list = [node.get_node() for node in nodes]
        response = { "Nodes": nodes_list}
        return json.dumps(response), 200      

# Get all Nodes================================================================
# @app.route('/node', methods = ['GET'])
# def getNodes():
#     global nodes
#     response = { "Nodes": [node.address for node in nodes]}
#     return jsonify(response), 200

# Remove node==================================================================
@app.route('/node/<address>', methods = ['DELETE'])
def removeNode(address):
    global nodes
    nodes = [x for x in nodes if x.address!=address]
    #Update for all nodes
    for node in nodes:
        node.nodes = nodes
    response = {"Message": 
                f"Node {address} has been removed from the network."}
    return jsonify(response), 200
# =============================================================================

# 2. Mempool===================================================================

# Add and get transaction======================================================
@app.route('/transaction', methods = ['POST', 'GET'])
def addTransaction():
    global mempool
    if request.method == 'POST':
        transaction = request.get_json() #{amount:, sender:, receiver:}
        transaction_keys = ['sender', 'receiver', 'amount']
        if not all(key in transaction for key in transaction_keys):
            return 'Some elements of the transaction are missing', 400
        mempool.add_transaction(transaction.get('amount'), 
                                transaction.get('sender'), 
                                transaction.get('receiver'))
        response = {"Message": "Transaction added successfully."}
        return jsonify(response),201
    
    if request.method == 'GET':
        response = {"Mempool": mempool.get_mempool()}
        return response, 200
        
# Remove a transaction=========================================================
@app.route('/transaction/<id>', methods = ['DELETE'])
def removeTransaction(id):
    global mempool
    mempool.transactions = [x for x in mempool.transactions if x.id!=id]
    response = {"Message": 
                f"Transaction {id} has been removed from the mempool."}
    return jsonify(response), 200
# =============================================================================

# =============================================================================
# To do: Nodes and blockchain
#     1. Check the mempool, if transactions found, start mining race for all
#     2. 2-5 transactions per block, add block
#     3. Update mempool again
#     4. Update transaction state and wallets 
# =============================================================================

# 3. Blockchain================================================================

# Mining a new block
@app.route('/mine_block', methods = ['GET'])
def mine_block():
    global stop_threads, last_task, nodes, mempool
    if len(mempool.transactions) < 1 :
        response = {"Message": 
                    "There must be atleast 1 transaction in the Mempool."}
        return jsonify(response), 428
    
    if len(nodes) < 2 :
        response = {"Message": "There must be atleast 2 nodes in the System."}
        return jsonify(response), 428
    
    stop_threads = False
    last_task = ""
    # Get number of transactions to be mined
    t_max = 5 if len(mempool.transactions)>5 else len(mempool.transactions)
    
    # Begin mining
    
    # 1. Create process threads for each node
    # 2. Start the threads for each node
    threads = []
    counter = 0
    
    for i in range(len(nodes)):
        thread_no = i
        t = threading.Thread(target = nodes[i].mine_block, 
                             name = str(thread_no), 
                             args = [t_max])
        threads.append(t)
        t.start()

    # 3. Join the threads (Joined with main thread, when complete)
    for thread in threads:
        thread.join()
    
    # 4. Update the mempool
    mempool.transactions = mempool.transactions[t_max:]
    
    
    #Prepare a response
    response = nodes[int(last_task)].blockchain.get_previous_block().get_block()
    
    return jsonify(response), 201

# Sync chain (with the longest chain)
@app.route('/chain_sync', methods = ['GET'])
def chain_sync():
    global nodes
    
    # 1. Find Longest chain
    longest_chain_node = max(nodes, 
                             key = lambda node: len(node.blockchain.chain))
    longest_chain = longest_chain_node.blockchain.chain
    
    # 2. Replace the longest chain for all blocks
    for node in nodes:
        node.blockchain.chain = longest_chain
    
    response = {"Message": "Chain has been synced."}
    return response, 200    

# Running the app
app.run(host = '0.0.0.0', port = 5000)
