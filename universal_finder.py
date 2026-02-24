#!/usr/bin/env python3
"""
UNIVERSAL CRYPTO WALLET FINDER v4.0
Multi-chain support: Bitcoin, Ethereum, Solana, BNB Chain, Base
No API keys required - uses public endpoints and web scraping
"""

import os
import sys
import json
import time
import hashlib
import secrets
import requests
import sqlite3
import random
import base58
import struct
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import signal
from pathlib import Path
import re
from collections import defaultdict
import urllib.parse
import socket

# ============================================
# COLOR CODES
# ============================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'

# ============================================
# CHAIN CONFIGURATIONS
# ============================================

class ChainConfig:
    """Configuration for each supported blockchain"""
    
    # Bitcoin
    BITCOIN = {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'decimal': 8,
        'address_length': [26, 35],
        'address_prefix': ['1', '3', 'bc1'],
        'explorer': 'https://blockchain.info/q/addressbalance/{}',
        'explorer2': 'https://chain.api.btc.com/v3/address/{}',
        'rpc': 'https://blockstream.info/api/address/{}',
        'type': 'utxo'
    }
    
    # Ethereum and EVM chains
    ETHEREUM = {
        'name': 'Ethereum',
        'symbol': 'ETH',
        'decimal': 18,
        'address_length': 42,
        'address_prefix': '0x',
        'explorer': 'https://api.etherscan.io/api?module=account&action=balance&address={}&tag=latest',
        'explorer2': 'https://eth.llamarpc.com',
        'type': 'evm'
    }
    
    BNB = {
        'name': 'BNB Chain',
        'symbol': 'BNB',
        'decimal': 18,
        'address_length': 42,
        'address_prefix': '0x',
        'explorer': 'https://api.bscscan.com/api?module=account&action=balance&address={}&tag=latest',
        'explorer2': 'https://bsc-dataseed.binance.org',
        'type': 'evm'
    }
    
    BASE = {
        'name': 'Base',
        'symbol': 'BASE',
        'decimal': 18,
        'address_length': 42,
        'address_prefix': '0x',
        'explorer': 'https://api.basescan.org/api?module=account&action=balance&address={}&tag=latest',
        'explorer2': 'https://mainnet.base.org',
        'type': 'evm'
    }
    
    # Solana
    SOLANA = {
        'name': 'Solana',
        'symbol': 'SOL',
        'decimal': 9,
        'address_length': 44,
        'address_prefix': [],
        'explorer': 'https://api.mainnet-beta.solana.com',
        'explorer2': 'https://solana-api.projectserum.com',
        'type': 'solana'
    }
    
    # Available chains
    CHAINS = {
        'btc': BITCOIN,
        'eth': ETHEREUM,
        'bnb': BNB,
        'base': BASE,
        'sol': SOLANA
    }

# ============================================
# WALLET GENERATORS
# ============================================

class WalletGenerator:
    """Generate wallets for different blockchains"""
    
    @staticmethod
    def generate_btc() -> Tuple[str, str]:
        """Generate Bitcoin wallet (simplified - for demo)"""
        # In production, use proper Bitcoin library
        private_key = secrets.token_hex(32)
        
        # Simple address derivation (placeholder)
        # In reality, this requires proper Bitcoin cryptography
        addr_hash = hashlib.sha256(private_key.encode()).hexdigest()
        addr_hash2 = hashlib.sha256(addr_hash.encode()).hexdigest()
        
        # Create a Bitcoin-like address (simplified)
        prefix = random.choice(['1', '3', 'bc1'])
        if prefix == 'bc1':
            address = prefix + addr_hash2[:38]
        else:
            address = prefix + addr_hash2[:33]
        
        return private_key, address
    
    @staticmethod
    def generate_evm() -> Tuple[str, str]:
        """Generate Ethereum/BNB/Base wallet"""
        private_key = '0x' + secrets.token_hex(32)
        
        # Derive address (simplified - in production use eth_account)
        private_key_bytes = bytes.fromhex(private_key[2:])
        public_key = hashlib.sha256(private_key_bytes).hexdigest()
        address = '0x' + hashlib.sha256(public_key.encode()).hexdigest()[:40]
        
        return private_key, address
    
    @staticmethod
    def generate_solana() -> Tuple[str, str]:
        """Generate Solana wallet (simplified)"""
        private_key = secrets.token_hex(64)
        
        # Solana addresses are base58 encoded public keys
        # Simplified version
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        address = base58.b58encode(bytes.fromhex(public_key[:64])).decode()
        
        return private_key, address
    
    @classmethod
    def generate(cls, chain: str) -> Tuple[str, str, str]:
        """Generate wallet for specified chain"""
        chain = chain.lower()
        
        if chain in ['btc', 'bitcoin']:
            priv, addr = cls.generate_btc()
            return priv, addr, 'btc'
        elif chain in ['eth', 'ethereum']:
            priv, addr = cls.generate_evm()
            return priv, addr, 'eth'
        elif chain in ['bnb', 'bsc']:
            priv, addr = cls.generate_evm()
            return priv, addr, 'bnb'
        elif chain in ['base']:
            priv, addr = cls.generate_evm()
            return priv, addr, 'base'
        elif chain in ['sol', 'solana']:
            priv, addr = cls.generate_solana()
            return priv, addr, 'sol'
        else:
            raise ValueError(f"Unsupported chain: {chain}")

# ============================================
# BALANCE CHECKERS (No API Keys)
# ============================================

class BalanceChecker:
    """Check balances across multiple chains using public endpoints"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache = {}
        self.failures = defaultdict(int)
    
    def check_btc(self, address: str) -> float:
        """Check Bitcoin balance using public APIs"""
        endpoints = [
            f"https://blockchain.info/q/addressbalance/{address}",
            f"https://chain.api.btc.com/v3/address/{address}",
            f"https://blockstream.info/api/address/{address}"
        ]
        
        for url in endpoints:
            try:
                if 'blockchain.info' in url:
                    response = self.session.get(url, timeout=5)
                    if response.status_code == 200:
                        balance = int(response.text) / 100000000  # sat to BTC
                        return balance
                
                elif 'btc.com' in url:
                    response = self.session.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('data', {}).get('balance'):
                            balance = data['data']['balance'] / 100000000
                            return balance
                
                elif 'blockstream.info' in url:
                    response = self.session.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('chain_stats', {}).get('funded_txo_sum'):
                            balance = (data['chain_stats']['funded_txo_sum'] - 
                                     data['chain_stats']['spent_txo_sum']) / 100000000
                            return balance
            except:
                continue
        
        return 0.0
    
    def check_evm(self, address: str, chain: str) -> float:
        """Check EVM chain balance using public RPC"""
        rpc_urls = {
            'eth': [
                'https://eth.llamarpc.com',
                'https://rpc.ankr.com/eth',
                'https://cloudflare-eth.com'
            ],
            'bnb': [
                'https://bsc-dataseed.binance.org',
                'https://bsc-dataseed1.defibit.io',
                'https://bsc-dataseed1.ninicoin.io'
            ],
            'base': [
                'https://mainnet.base.org',
                'https://base.llamarpc.com',
                'https://base.blockpi.network/v1/rpc/public'
            ]
        }
        
        # Prepare JSON-RPC request
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1
        }
        
        for url in rpc_urls.get(chain, []):
            try:
                response = self.session.post(url, json=payload, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data:
                        balance_wei = int(data['result'], 16)
                        return balance_wei / 1e18
            except:
                continue
        
        return 0.0
    
    def check_solana(self, address: str) -> float:
        """Check Solana balance using public RPC"""
        rpc_urls = [
            'https://api.mainnet-beta.solana.com',
            'https://solana-api.projectserum.com',
            'https://rpc.ankr.com/solana'
        ]
        
        payload = {
            "jsonrpc": "2.0",
            "method": "getBalance",
            "params": [address],
            "id": 1
        }
        
        for url in rpc_urls:
            try:
                response = self.session.post(url, json=payload, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and 'value' in data['result']:
                        return data['result']['value'] / 1e9
            except:
                continue
        
        return 0.0
    
    def check_all(self, address: str, chain: str) -> float:
        """Check balance for address on specified chain"""
        chain = chain.lower()
        
        if chain == 'btc':
            return self.check_btc(address)
        elif chain in ['eth', 'bnb', 'base']:
            return self.check_evm(address, chain)
        elif chain == 'sol':
            return self.check_solana(address)
        
        return 0.0

# ============================================
# WEB SCRAPING INTELLIGENCE (No API Keys)
# ============================================

class WebIntelligence:
    """Gather intelligence from public web sources without APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.known_patterns = defaultdict(list)
    
    def scrape_rich_addresses(self) -> Dict[str, List[str]]:
        """Scrape known rich addresses from public sources"""
        rich_addresses = defaultdict(list)
        
        sources = [
            ('btc', 'https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html'),
            ('eth', 'https://bitinfocharts.com/top-100-richest-ethereum-addresses.html'),
            ('bnb', 'https://bitinfocharts.com/top-100-richest-binance%20coin-addresses.html'),
        ]
        
        for chain, url in sources:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Simple regex to find addresses
                    if chain == 'btc':
                        addresses = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', response.text)
                    else:
                        addresses = re.findall(r'0x[a-fA-F0-9]{40}', response.text)
                    
                    rich_addresses[chain] = list(set(addresses))[:100]
                    print(f"{Colors.GREEN}✅ Found {len(rich_addresses[chain])} rich {chain.upper()} addresses{Colors.END}")
            except:
                continue
        
        return rich_addresses
    
    def analyze_address_patterns(self, addresses: List[str]) -> Dict:
        """Analyze patterns in known addresses"""
        patterns = {
            'prefixes': defaultdict(int),
            'suffixes': defaultdict(int),
            'lengths': defaultdict(int),
            'char_freq': defaultdict(int),
            'vanity_patterns': []
        }
        
        for addr in addresses:
            if len(addr) > 10:
                # Prefix analysis (first 6 chars)
                prefix = addr[:6]
                patterns['prefixes'][prefix] += 1
                
                # Suffix analysis (last 6 chars)
                suffix = addr[-6:]
                patterns['suffixes'][suffix] += 1
                
                # Length analysis
                patterns['lengths'][len(addr)] += 1
                
                # Character frequency
                for c in addr[2:]:  # Skip 0x for EVM
                    patterns['char_freq'][c] += 1
                
                # Vanity patterns (repeating chars, sequential)
                if re.search(r'(.)\1{3,}', addr):
                    patterns['vanity_patterns'].append(addr)
        
        return patterns

# ============================================
# INTELLIGENT WALLET GENERATOR
# ============================================

class IntelligentGenerator:
    """Generates wallets based on learned patterns"""
    
    def __init__(self, patterns: Dict):
        self.patterns = patterns
        self.popular_prefixes = sorted(patterns.get('prefixes', {}).items(), 
                                      key=lambda x: x[1], reverse=True)[:100]
        self.popular_suffixes = sorted(patterns.get('suffixes', {}).items(),
                                      key=lambda x: x[1], reverse=True)[:100]
    
    def generate_targeted(self, chain: str, count: int) -> List[Tuple[str, str, str]]:
        """Generate wallets targeting popular patterns"""
        wallets = []
        
        for _ in range(count):
            # Try to match popular prefixes/suffixes
            if random.random() < 0.3 and self.popular_prefixes:
                target_prefix = random.choice(self.popular_prefixes)[0]
                # Generate wallet that might match prefix (simplified)
                # In reality, this would require address generation with specific prefix
            
            # Generate random wallet as fallback
            priv, addr, chain = WalletGenerator.generate(chain)
            wallets.append((priv, addr, chain))
        
        return wallets

# ============================================
# MAIN SCANNER
# ============================================

class UniversalScanner:
    """Main scanning engine"""
    
    def __init__(self, chains: List[str]):
        self.chains = chains
        self.checker = BalanceChecker()
        self.web_intel = WebIntelligence()
        self.generator = WalletGenerator()
        self.total_checked = 0
        self.found_wallets = []
        self.start_time = time.time()
        self.running = True
        self.lock = threading.RLock()
        self.stats = defaultdict(int)
        
        # Load intelligence
        print(f"{Colors.CYAN}🧠 Gathering blockchain intelligence...{Colors.END}")
        self.rich_addresses = self.web_intel.scrape_rich_addresses()
        self.patterns = self.web_intel.analyze_address_patterns(
            sum(self.rich_addresses.values(), [])
        )
        
        # Initialize intelligent generator
        self.intel_gen = IntelligentGenerator(self.patterns)
    
    def check_single(self, chain: str) -> Optional[Dict]:
        """Generate and check a single wallet"""
        private_key, address, chain = WalletGenerator.generate(chain)
        balance = self.checker.check_all(address, chain)
        
        with self.lock:
            self.total_checked += 1
            self.stats[chain] += 1
            
            if balance > 0:
                wallet = {
                    'chain': chain.upper(),
                    'private_key': private_key,
                    'address': address,
                    'balance': balance,
                    'found_at': datetime.now().isoformat(),
                    'checked': self.total_checked
                }
                self.found_wallets.append(wallet)
                self.stats['found'] += 1
                self.stats[f'{chain}_found'] += 1
                self.stats['total_eth'] += balance
                return wallet
        
        return None
    
    def worker(self, task_queue: queue.Queue, result_queue: queue.Queue):
        """Worker thread function"""
        while self.running:
            try:
                chain = task_queue.get(timeout=1)
                result = self.check_single(chain)
                if result:
                    result_queue.put(result)
                task_queue.task_done()
            except queue.Empty:
                continue
    
    def print_progress(self):
        """Print progress statistics"""
        elapsed = time.time() - self.start_time
        rate = self.total_checked / elapsed if elapsed > 0 else 0
        
        stats_line = f"\r{Colors.CYAN}[⚡] Total: {self.total_checked:,} | "
        for chain in self.chains:
            stats_line += f"{chain.upper()}: {self.stats[chain]:,} | "
        stats_line += f"{Colors.GREEN}[💰] Found: {self.stats['found']} | "
        stats_line += f"{Colors.YELLOW}[📊] Rate: {rate:.0f}/s | "
        stats_line += f"{Colors.MAGENTA}[💎] ETH: {self.stats['total_eth']:.6f}{Colors.END}"
        
        sys.stdout.write(stats_line)
        sys.stdout.flush()
    
    def save_found(self):
        """Save found wallets to file"""
        if not self.found_wallets:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs('found_wallets', exist_ok=True)
        
        # Save by chain
        for chain in self.chains:
            chain_wallets = [w for w in self.found_wallets if w['chain'].lower() == chain.lower()]
            if chain_wallets:
                filename = f"found_wallets/{chain}_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(chain_wallets, f, indent=2)
                
                # Save private keys
                priv_file = f"found_wallets/{chain}_private_{timestamp}.txt"
                with open(priv_file, 'w') as f:
                    for w in chain_wallets:
                        f.write(f"# {w['address']} - {w['balance']} {w['chain']}\n")
                        f.write(f"{w['private_key']}\n\n")
        
        # Save all together
        all_file = f"found_wallets/all_{timestamp}.json"
        with open(all_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_checked': self.total_checked,
                'found_count': len(self.found_wallets),
                'wallets': self.found_wallets
            }, f, indent=2)
        
        print(f"\n{Colors.GREEN}✅ Saved {len(self.found_wallets)} wallets{Colors.END}")
    
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C"""
        print(f"\n{Colors.YELLOW}🛑 Stopping...{Colors.END}")
        self.running = False
        self.save_found()
        self.print_summary()
        sys.exit(0)
    
    def print_summary(self):
        """Print final summary"""
        elapsed = time.time() - self.start_time
        rate = self.total_checked / elapsed if elapsed > 0 else 0
        
        print(f"\n\n{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗")
        print(f"║                 UNIVERSAL SCAN SUMMARY                            ║")
        print(f"╠══════════════════════════════════════════════════════════════╣")
        print(f"║  Total Wallets Checked: {self.total_checked:>28,} ║")
        
        for chain in self.chains:
            print(f"║  {chain.upper():<12} Checked: {self.stats[chain]:>26,} ║")
        
        print(f"║  {'─' * 54}║")
        print(f"║  Wallets with Balance:  {self.stats['found']:>28} ║")
        
        for chain in self.chains:
            found = self.stats.get(f'{chain}_found', 0)
            if found > 0:
                print(f"║  {chain.upper():<12} Found: {found:>29} ║")
        
        print(f"║  Total Value:           {self.stats['total_eth']:>28.6f} ETH ║")
        print(f"║  Time Elapsed:          {timedelta(seconds=int(elapsed)):>28} ║")
        print(f"║  Average Speed:         {rate:>28.0f} wallets/s ║")
        print(f"╚══════════════════════════════════════════════════════════════╝{Colors.END}")
    
    def run(self, duration: int = None):
        """Main run loop"""
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗")
        print(f"║         UNIVERSAL CRYPTO WALLET FINDER v4.0                    ║")
        print(f"║         Multi-Chain: {', '.join(c.upper() for c in self.chains)}                  ║")
        print(f"╚══════════════════════════════════════════════════════════════╝{Colors.END}\n")
        
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Create queues
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        
        # Start workers
        threads = []
        for _ in range(50):  # 50 threads
            t = threading.Thread(target=self.worker, args=(task_queue, result_queue))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Fill initial tasks
        for _ in range(10000):
            chain = random.choice(self.chains)
            task_queue.put(chain)
        
        # Progress reporter
        def report_progress():
            while self.running:
                self.print_progress()
                time.sleep(0.1)
        
        report_thread = threading.Thread(target=report_progress)
        report_thread.daemon = True
        report_thread.start()
        
        # Result processor
        def process_results():
            while self.running:
                try:
                    wallet = result_queue.get(timeout=1)
                    print(f"\n{Colors.GREEN}🎉 FOUND {wallet['chain']} WALLET WITH BALANCE!{Colors.END}")
                    print(f"   Address: {Colors.YELLOW}{wallet['address']}{Colors.END}")
                    print(f"   Balance: {Colors.GREEN}{wallet['balance']} {wallet['chain']}{Colors.END}")
                    print(f"   Private: {Colors.RED}{wallet['private_key'][:30]}...{Colors.END}")
                    
                    # Save every 10 finds
                    if len(self.found_wallets) % 10 == 0:
                        self.save_found()
                        
                except queue.Empty:
                    continue
        
        result_thread = threading.Thread(target=process_results)
        result_thread.daemon = True
        result_thread.start()
        
        # Main loop
        start_time = time.time()
        while self.running:
            if duration and time.time() - start_time > duration:
                break
            
            # Keep queue filled
            if task_queue.qsize() < 1000:
                for _ in range(100):
                    chain = random.choice(self.chains)
                    task_queue.put(chain)
            
            time.sleep(0.01)
        
        # Wait for completion
        task_queue.join()
        time.sleep(1)
        
        self.save_found()
        self.print_summary()

# ============================================
# MAIN ENTRY POINT
# ============================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Universal Crypto Wallet Finder')
    parser.add_argument('--chains', '-c', nargs='+', 
                       choices=['btc', 'eth', 'bnb', 'base', 'sol', 'all'],
                       default=['eth'], help='Chains to scan')
    parser.add_argument('--threads', '-t', type=int, default=50, help='Number of threads')
    parser.add_argument('--duration', '-d', type=int, help='Scan duration in seconds')
    parser.add_argument('--min-balance', '-m', type=float, default=0.000001, 
                       help='Minimum balance to report')
    
    args = parser.parse_args()
    
    # Parse chains
    if 'all' in args.chains:
        chains = ['btc', 'eth', 'bnb', 'base', 'sol']
    else:
        chains = args.chains
    
    print(f"{Colors.GREEN}🚀 Starting Universal Scanner on chains: {', '.join(c.upper() for c in chains)}{Colors.END}")
    print(f"{Colors.YELLOW}📡 Using public endpoints only - no API keys required{Colors.END}")
    print(f"{Colors.RED}⚠️  This is for educational purposes only{Colors.END}\n")
    
    scanner = UniversalScanner(chains)
    scanner.run(args.duration)

if __name__ == "__main__":
    main()