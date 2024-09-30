import os
import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Initialize Web3 provider
w3 = Web3(Web3.HTTPProvider(os.getenv("SEPOLIA_NODE_URL")))

# AGIX contract details
AGIX_CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("AGIX_CONTRACT_ADDR"))

with open("agix_abi.json", "r") as file:
    AGIX_ABI = json.load(file)

# Sender's and receipent information
FROM_PRIVATE_KEY, FROM_ADDRESS = os.getenv("FROM_PRIVATE_KEY"), os.getenv(
    "FROM_ADDRESS"
)
TO_PRIVATE_KEY, TO_ADDRESS = os.getenv("TO_PRIVATE_KEY"), os.getenv("TO_ADDRESS")

PRICE_COEF = 0.1  # agix per user request
DEFAULT_AMOUNT = min(PRICE_COEF * 10, 1)  # This will transfer x AGIX token


class AGIX_CONTRACT:
    def __init__(self, from_private_key=None, to_private_key=None):
        self.contract = w3.eth.contract(address=AGIX_CONTRACT_ADDRESS, abi=AGIX_ABI)
        self.from_private_key = (
            FROM_PRIVATE_KEY if from_private_key is None else from_private_key
        )
        self.to_private_key = (
            TO_PRIVATE_KEY if to_private_key is None else to_private_key
        )

        self.from_account = self.get_account(self.from_private_key)
        self.to_account = self.get_account(self.to_private_key)
        self.token_decimals = self.get_token_details()

    def get_account(self, private_key):
        return Account.from_key(private_key)

    # Calculate AGIX needed for the requests
    def calculate_agix(self, number_of_user_requests):
        # Default: 10 requests = 1 AGIX
        required_agix = number_of_user_requests * PRICE_COEF
        agix_balance = self.get_balance(self.from_account.address)
        remaining_agix = agix_balance - required_agix
        return required_agix, agix_balance, remaining_agix

    def get_token_details(self):
        """Fetch and print token decimals and the balance of the sender."""
        try:
            token_decimals = self.contract.functions.decimals().call()
            return token_decimals
        except Exception as e:
            print(f"Error fetching token details: {e}")
            return None

    def get_balance(self, account_address):
        """Fetch the token balance for the given account."""
        try:
            balance = self.contract.functions.balanceOf(account_address).call()
            agix_balance = balance / (10**self.token_decimals)
            return agix_balance
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None

    def create_transaction(self, amount, gas_limit, nonce):
        """Build and sign the transaction."""
        try:
            tx = self.contract.functions.transfer(
                self.to_account.address, amount
            ).build_transaction(
                {
                    "from": self.from_account.address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "gasPrice": w3.eth.gas_price,
                    "chainId": 11155111,
                }
            )
            signed_tx = self.from_account.sign_transaction(tx)
            return signed_tx
        except Exception as e:
            print(f"Error creating transaction: {e}")
            return None

    def transfer_agix(self, amount):
        """Execute the AGIX transfer."""
        try:
            if self.token_decimals is None:
                return None

            balance = self.get_balance(self.from_account.address)
            if balance is None:
                return None

            amount_in_smallest_unit = int(amount * (10**self.token_decimals))
            if balance < amount:
                print(
                    f"Insufficient balance. Trying to send {amount} AGIX, but only {balance / (10 ** self.token_decimals)} AGIX is available."
                )
                return "Insufficient balance"

            nonce = w3.eth.get_transaction_count(self.from_account.address)
            estimated_gas = self.contract.functions.transfer(
                self.to_account.address, amount_in_smallest_unit
            ).estimate_gas({"from": self.from_account.address, "nonce": nonce})
            gas_limit = int(estimated_gas * 1.2)

            signed_tx = self.create_transaction(
                amount_in_smallest_unit, gas_limit, nonce
            )
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_receipt

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("Exception details:", e.__class__.__name__)
            traceback.print_exc()
            return None


if __name__ == "__main__":
    if not w3.is_connected():
        print("Not connected to Ethereum network")
    else:
        print("Connected to Ethereum network")
        agix_contract = AGIX_CONTRACT()

        print(f"FROM {agix_contract.from_account.address}")
        print(
            f"AGIX Balance: {agix_contract.get_balance(agix_contract.from_account.address)}"
        )
        print(f"TO: {agix_contract.to_account.address}")
        print(
            f"AGIX Balance: {agix_contract.get_balance(agix_contract.to_account.address)}"
        )

        '''        receipt = agix_contract.transfer_agix(1)
                if receipt:
                    print(
                        f"Transaction successful. Transaction hash: {receipt['transactionHash'].hex()}"
                    )
                    print(f"link: https://sepolia.etherscan.io/tx/{receipt['transactionHash'].hex()}")
                    print("NEW FROM:")
                    print(f"AGIX Balance: {agix_contract.get_balance(agix_contract.from_account.address)}")
                    print("NEW TO:")
                    print(f"AGIX Balance: {agix_contract.get_balance(agix_contract.to_account.address)}")
                else:
                    print("Transaction failed")'''
