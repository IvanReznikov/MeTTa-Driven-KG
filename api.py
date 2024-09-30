import json
from fastapi import FastAPI, HTTPException, Body, Request
from backend import AGIX_CONTRACT, PRICE_COEF
from pydantic import BaseModel

app = FastAPI()
agix_contract = AGIX_CONTRACT()


class PurchaseRequest(BaseModel):
    user_id: int
    requests: int


class ConfirmPurchaseRequest(BaseModel):
    user_id: int
    to_address: str
    amount_agix: float


# Load users from JSON file
@app.get("/get_users")
def load_users():
    with open("users_db.json", "r") as f:
        return json.load(f)


# Write users back to JSON file after updating balances
def save_users(users):
    with open("users_db.json", "w") as f:
        json.dump(users, f, indent=4)


# Get user by ID
def get_user_by_id(user_id):
    users = load_users()
    for user in users:
        if user["id"] == user_id:
            return user
    return None


# Route to get user details (request balance)
@app.get("/user/{user_id}")
def get_user_balance(user_id: int):
    user = get_user_by_id(user_id)
    if user:
        return {"name": user["name"], "request_balance": user["request_balance"]}
    else:
        raise HTTPException(status_code=404, detail="User not found")


# Route to purchase requests
@app.post("/purchase")
def purchase_requests(payload: dict = Body(...)):
    user_id = payload["user_id"]
    num_requests = payload["num_requests"]
    users = load_users()
    user = get_user_by_id(user_id)
    if user:
        user["request_balance"] += num_requests
        save_users(users)  # Save the updated balance back to the file
        return {"new_balance": user["request_balance"]}
    else:
        raise HTTPException(status_code=404, detail="User not found")


# Route to run a paid query
@app.post("/run_paid_query")
def run_paid_query(user_id: int = Body(..., embed=True)):
    users = load_users()
    user = get_user_by_id(user_id)
    if user:
        if user["request_balance"] > 0:
            idx = users.index(user)
            user["request_balance"] -= 1  # Deduct 1 request
            users[idx] = user
            save_users(users)  # Save the updated balance back to the file
            return {
                "remaining_balance": user["request_balance"],
                "result": "Query executed successfully!",
            }
        else:
            raise HTTPException(status_code=400, detail="Insufficient request balance")
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.post("/purchase_requests")
def purchase_requests(payload: dict = Body(...)):
    user_id = payload["user_id"]
    num_requests = payload["num_requests"]
    user = get_user_by_id(user_id)
    # try:
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    required_agix, agix_balance, remaining_agix = agix_contract.calculate_agix(
        num_requests
    )

    if required_agix > agix_balance:
        raise HTTPException(status_code=400, detail="Insufficient AGIX balance")

    return {
        "user_id": user_id,
        "agix_balance": agix_balance,
        "required_agix": required_agix,
        "remaining_agix": remaining_agix,
    }


@app.post("/confirm_purchase")
def confirm_purchase(payload: dict = Body(...)):
    user_id = payload["user_id"]
    amount_agix = payload["amount_agix"]
    users = load_users()
    user = get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tx_receipt = agix_contract.transfer_agix(
        amount_agix,
    )

    if tx_receipt:
        print(f"FROM {agix_contract.from_account.address}")
        print(
            f"AGIX Balance: {agix_contract.get_balance(agix_contract.from_account.address)}"
        )
        print(f"TO: {agix_contract.to_account.address}")
        print(
            f"AGIX Balance: {agix_contract.get_balance(agix_contract.to_account.address)}"
        )

        idx = users.index(user)
        user["request_balance"] += int(amount_agix / PRICE_COEF)
        users[idx] = user
        save_users(users)

        print("=" * 20)
        print(
            f"Transaction successful. Transaction hash: {tx_receipt['transactionHash'].hex()}"
        )
        print(f"link: https://sepolia.etherscan.io/tx/0x{tx_receipt['transactionHash'].hex()}")
        print("=" * 20)
        print(f"FROM {agix_contract.from_account.address}")
        print(
            f"NEW AGIX Balance: {agix_contract.get_balance(agix_contract.from_account.address)}"
        )
        print(f"TO: {agix_contract.to_account.address}")
        print(
            f"NEW AGIX Balance: {agix_contract.get_balance(agix_contract.to_account.address)}"
        )

        return {
            "status": "Transaction successful",
            "transaction_hash": tx_receipt["transactionHash"].hex(),
        }
    else:
        raise HTTPException(status_code=400, detail="Transaction failed")

