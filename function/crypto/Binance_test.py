import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_binance_data(symbol="BTCUSDT", interval="1h", limit=24):
    """
    Binance API로 원하는 시간 단위의 데이터 가져오기
    - symbol: 거래쌍 (예: BTCUSDT, ETHUSDT)
    - interval: 시간 간격 (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
    - limit: 가져올 캔들 개수 (최대 1000개)
    """
    
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # 데이터프레임으로 변환
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # 숫자형으로 변환
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    
    # 시간 변환
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    
    return df

def calculate_pi_cycle_top(df):
    """
    Pi Cycle Top Indicator 계산
    - 111일 SMA (Simple Moving Average)
    - 350일 SMA * 2
    - 두 값이 교차할 때가 상단 신호
    """
    
    # 111일 SMA 계산
    df['sma_111'] = df['close'].rolling(window=111).mean()
    
    # 350일 SMA 계산
    df['sma_350'] = df['close'].rolling(window=350).mean()
    
    # 350일 SMA * 2
    df['sma_350_x2'] = df['sma_350'] * 2
    
    # Pi Cycle Top 신호 계산
    df['pi_cycle_signal'] = df['sma_111'] - df['sma_350_x2']
    
    # 상단 신호 (111일 SMA가 350일 SMA * 2를 상향 돌파)
    df['pi_cycle_top'] = (df['sma_111'] > df['sma_350_x2']) & (df['sma_111'].shift(1) <= df['sma_350_x2'].shift(1))
    
    # 하단 신호 (111일 SMA가 350일 SMA * 2를 하향 돌파)
    df['pi_cycle_bottom'] = (df['sma_111'] < df['sma_350_x2']) & (df['sma_111'].shift(1) >= df['sma_350_x2'].shift(1))
    
    return df

def get_pi_cycle_analysis(symbol="BTCUSDT", interval="1d", limit=500):
    """
    Pi Cycle Top Indicator 분석
    - 최소 350일 이상의 데이터가 필요하므로 limit을 충분히 설정
    """
    
    # 충분한 데이터 가져오기 (최소 400일)
    if limit < 400:
        limit = 400
    
    # 데이터 가져오기
    df = get_binance_data(symbol, interval, limit)
    
    # Pi Cycle Top 계산
    df = calculate_pi_cycle_top(df)
    
    # 최신 데이터만 사용 (NaN 값 제거)
    df_clean = df.dropna()
    
    if len(df_clean) == 0:
        print("충분한 데이터가 없습니다. 더 많은 데이터를 가져오세요.")
        return df, None
    
    # 현재 상태 분석
    current_price = df_clean['close'].iloc[-1]
    current_sma_111 = df_clean['sma_111'].iloc[-1]
    current_sma_350_x2 = df_clean['sma_350_x2'].iloc[-1]
    current_signal = df_clean['pi_cycle_signal'].iloc[-1]
    
    # 최근 상단/하단 신호 확인
    recent_top_signals = df_clean[df_clean['pi_cycle_top'] == True].tail(3)
    recent_bottom_signals = df_clean[df_clean['pi_cycle_bottom'] == True].tail(3)
    
    # 결과 출력
    print(f"=== {symbol} Pi Cycle Top Indicator 분석 ===")
    print(f"현재 가격: {current_price:.2f} USDT")
    print(f"111일 SMA: {current_sma_111:.2f} USDT")
    print(f"350일 SMA * 2: {current_sma_350_x2:.2f} USDT")
    print(f"신호 값: {current_signal:.2f} USDT")
    
    if current_sma_111 > current_sma_350_x2:
        print("상태: 상단 신호 구간 (111일 SMA > 350일 SMA * 2)")
        print(f"상단 신호 강도: {((current_sma_111 / current_sma_350_x2) - 1) * 100:.2f}%")
        print("시장 과열 상태")
    else:
        print("상태: 하단 신호 구간 (111일 SMA < 350일 SMA * 2)")
        print(f"하단 신호 강도: {((current_sma_350_x2 / current_sma_111) - 1) * 100:.2f}%")
        print("시장 미과열 상태")
    
    if len(recent_top_signals) > 0:
        print(f"\n최근 상단 신호: {recent_top_signals['open_time'].iloc[-1].strftime('%Y-%m-%d')}")
    
    if len(recent_bottom_signals) > 0:
        print(f"최근 하단 신호: {recent_bottom_signals['open_time'].iloc[-1].strftime('%Y-%m-%d')}")
    
    # 분석 기간
    print(f"\n분석 기간: {df_clean['open_time'].iloc[0].strftime('%Y-%m-%d')} ~ {df_clean['open_time'].iloc[-1].strftime('%Y-%m-%d')}")
    print(f"총 데이터 수: {len(df_clean)}개")
    
    return df_clean, {
        'current_price': current_price,
        'sma_111': current_sma_111,
        'sma_350_x2': current_sma_350_x2,
        'signal': current_signal,
        'is_top_signal': current_sma_111 > current_sma_350_x2,
        'signal_strength': abs((current_sma_111 / current_sma_350_x2) - 1) * 100
    }

def calculate_metrics(df):
    """
    데이터프레임에서 다양한 통계 지표 계산
    """
    metrics = {
        'avg_price': df['close'].mean(),
        'avg_volume': df['volume'].mean(),
        'avg_volatility': ((df['high'] - df['low']) / df['low'] * 100).mean(),
        'max_price': df['high'].max(),
        'min_price': df['low'].min(),
        'price_change': df['close'].iloc[-1] - df['close'].iloc[0],
        'price_change_percent': ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100),
        'total_volume': df['volume'].sum(),
        'avg_trades': df['number_of_trades'].mean() if 'number_of_trades' in df.columns else None
    }
    
    return metrics

def get_crypto_analysis(symbol="BTCUSDT", interval="1h", limit=24):
    """
    암호화폐 데이터 분석 통합 함수
    """
    # 데이터 가져오기
    df = get_binance_data(symbol, interval, limit)
    
    # 통계 계산
    metrics = calculate_metrics(df)
    
    # 결과 출력
    print(f"=== {symbol} {interval} 간격 분석 (최근 {limit}개 데이터) ===")
    print(f"평균 가격: {metrics['avg_price']:.2f} USDT")
    print(f"최고가: {metrics['max_price']:.2f} USDT")
    print(f"최저가: {metrics['min_price']:.2f} USDT")
    print(f"평균 거래량: {metrics['avg_volume']:.4f} {symbol.replace('USDT', '')}")
    print(f"총 거래량: {metrics['total_volume']:.4f} {symbol.replace('USDT', '')}")
    print(f"평균 변동성: {metrics['avg_volatility']:.2f}%")
    print(f"가격 변화: {metrics['price_change']:.2f} USDT ({metrics['price_change_percent']:.2f}%)")
    
    if metrics['avg_trades']:
        print(f"평균 거래 횟수: {metrics['avg_trades']:.0f}회")
    
    print(f"분석 기간: {df['open_time'].iloc[0]} ~ {df['open_time'].iloc[-1]}")
    
    return df, metrics

# 사용 예시들
if __name__ == "__main__":
    # Pi Cycle Top Indicator 분석 (일봉 데이터, 500일)
    print("1. Pi Cycle Top Indicator 분석:")
    df_pi, pi_metrics = get_pi_cycle_analysis("BTCUSDT", "1d", 500)
    print()
    
    # 1시간 간격으로 24시간 데이터
    print("2. 1시간 간격 24시간 데이터:")
    df_1h, metrics_1h = get_crypto_analysis("BTCUSDT", "1h", 24)
    print()
    
    # 15분 간격으로 96개 데이터 (24시간)
    print("3. 15분 간격 24시간 데이터:")
    df_15m, metrics_15m = get_crypto_analysis("BTCUSDT", "15m", 96)
    print()
    
    # 4시간 간격으로 7일 데이터
    print("4. 4시간 간격 7일 데이터:")
    df_4h, metrics_4h = get_crypto_analysis("BTCUSDT", "4h", 42)
    print()
    
    # 이더리움 1시간 데이터
    print("5. 이더리움 1시간 데이터:")
    df_eth, metrics_eth = get_crypto_analysis("ETHUSDT", "1h", 24)