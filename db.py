from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    request_balance = Column(Integer, default=0)
    coins = Column(Integer, default=0)

    def purchase_requests(self, num_requests, cost_per_request):
        total_cost = num_requests * cost_per_request
        if self.coins >= total_cost:
            self.coins -= total_cost
            self.request_balance += num_requests
            return True
        return False

    def deduct_request(self):
        if self.request_balance > 0:
            self.request_balance -= 1
            return True
        return False
