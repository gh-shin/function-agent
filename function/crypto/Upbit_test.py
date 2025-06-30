import pyupbit

# 비트코인 현재가 조회
price = pyupbit.get_current_price("KRW-BTC")
print("비트코인 현재가:", price)