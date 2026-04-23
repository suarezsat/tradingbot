# Investigacion de estrategias Forex

- Fecha: 2026-04-23T22:22:40
- Spread supuesto: 0.5 pip(s)
- Pares nucleo: EURUSD, GBPUSD, USDJPY
- Pares validacion final: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD
- Años nucleo: 2021, 2022, 2023, 2024, 2025
- Backtests ejecutados: 1338

## Protocolo

- Cribado inicial de todas las estrategias con combinaciones aleatorias y costes de spread.
- Busqueda profunda solo sobre las mejores familias.
- Seleccion con validacion walk-forward 2021-2022->2023, 2022-2023->2024 y 2023-2024->2025.
- Validacion final ampliada sobre 2025 en seis pares mayores.

## Fuentes externas usadas

- Documentacion oficial de `backtesting.py` sobre `Backtest.optimize()` y el tratamiento de `spread`: https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html
- Hsu, Taylor y Wang (2016), sobre muchas reglas, control del data snooping y validacion fuera de muestra: https://www.sciencedirect.com/science/article/pii/S0022199616300472
- Neely y Weller (2003), sobre como la rentabilidad intradia desaparece facilmente al meter costes realistas: https://www.sciencedirect.com/science/article/pii/S0261560602001018
- Holmberg, Lonnbark y Lundstrom (2013), como justificacion para probar una familia ORB/rango inicial: https://www.sciencedirect.com/science/article/pii/S1544612312000438

## Top del cribado inicial

- RSI con niveles: score 10.64, retorno 4.25%, drawdown -22.82%.
- Bollinger + RSI: score 2.27, retorno 4.80%, drawdown -16.84%.
- Bollinger + RSI: score 1.90, retorno 3.49%, drawdown -17.26%.
- Bollinger + RSI: score -4.42, retorno 3.87%, drawdown -22.27%.
- Ruptura de sesion: score -10.14, retorno -3.88%, drawdown -17.66%.
- RSI2 con tendencia: score -12.73, retorno -6.77%, drawdown -19.68%.
- Ruptura de sesion: score -15.87, retorno -6.00%, drawdown -8.92%.
- EMA + RSI tendencia: score -17.41, retorno -10.88%, drawdown -20.20%.
- EMA + RSI tendencia: score -20.91, retorno -8.99%, drawdown -21.35%.
- Donchian Breakout: score -33.09, retorno -16.60%, drawdown -23.12%.

## Top de la busqueda profunda

- Bollinger + RSI {'stop_loss_pips': 6, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}: score 50.98, retorno 88.40%, drawdown -48.58%.
- Bollinger + RSI {'stop_loss_pips': 40, 'take_profit_pips': 120, 'usar_trailing_stop': True, 'trailing_stop_pips': 15, 'session_label': 'Londres', 'bollinger_periodo': 50, 'desviaciones': 2.0, 'rsi_periodo': 21}: score 11.29, retorno 8.55%, drawdown -14.60%.
- Bollinger + RSI {'stop_loss_pips': 12, 'take_profit_pips': 24, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Nueva York', 'bollinger_periodo': 50, 'desviaciones': 3.0, 'rsi_periodo': 7}: score 10.91, retorno 15.25%, drawdown -23.68%.
- Bollinger + RSI {'stop_loss_pips': 50, 'take_profit_pips': 80, 'usar_trailing_stop': True, 'trailing_stop_pips': 15, 'session_label': 'Londres', 'bollinger_periodo': 50, 'desviaciones': 2.0, 'rsi_periodo': 21}: score 7.16, retorno 5.14%, drawdown -12.03%.
- Bollinger + RSI {'stop_loss_pips': 30, 'take_profit_pips': 120, 'usar_trailing_stop': True, 'trailing_stop_pips': 30, 'session_label': 'Londres', 'bollinger_periodo': 20, 'desviaciones': 2.5, 'rsi_periodo': 14}: score 0.17, retorno 10.05%, drawdown -23.82%.
- RSI2 con tendencia {'stop_loss_pips': 6, 'take_profit_pips': 16, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Londres', 'ema_tendencia': 50, 'rsi_periodo': 5, 'umbral_largo': 10, 'umbral_corto': 90}: score -2.96, retorno -2.44%, drawdown -9.67%.
- Ruptura de sesion {'stop_loss_pips': 40, 'take_profit_pips': 60, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 15, 'hora_fin_operativa': 12, 'buffer_pips': 1.0}: score -3.50, retorno -1.68%, drawdown -6.20%.
- Bollinger + RSI {'stop_loss_pips': 40, 'take_profit_pips': 60, 'usar_trailing_stop': True, 'trailing_stop_pips': 15, 'session_label': 'Asiatica', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}: score -4.14, retorno -1.10%, drawdown -15.00%.
- RSI2 con tendencia {'stop_loss_pips': 40, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'ema_tendencia': 50, 'rsi_periodo': 5, 'umbral_largo': 10, 'umbral_corto': 90}: score -4.61, retorno -3.05%, drawdown -14.58%.
- RSI con niveles {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}: score -4.77, retorno -4.50%, drawdown -18.38%.

## Resultado walk-forward

- Bollinger + RSI: OOS medio 45.90%, score OOS 3.41, drawdown OOS -49.98%, folds positivos 2/3.
  - 2021-2022 -> 2023: retorno 147.24%, drawdown -40.25%, params {'stop_loss_pips': 6, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}
  - 2022-2023 -> 2024: retorno 21.14%, drawdown -46.91%, params {'stop_loss_pips': 6, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}
  - 2023-2024 -> 2025: retorno -30.66%, drawdown -62.77%, params {'stop_loss_pips': 6, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}
- RSI con niveles: OOS medio -6.16%, score OOS -7.04, drawdown OOS -18.75%, folds positivos 1/3.
  - 2021-2022 -> 2023: retorno -13.79%, drawdown -19.86%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
  - 2022-2023 -> 2024: retorno 3.62%, drawdown -20.20%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
  - 2023-2024 -> 2025: retorno -8.29%, drawdown -16.20%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
- Ruptura de sesion: OOS medio 1.60%, score OOS -16.54, drawdown OOS -23.53%, folds positivos 1/3.
  - 2021-2022 -> 2023: retorno 14.55%, drawdown -47.06%, params {'stop_loss_pips': 6, 'take_profit_pips': 80, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 45, 'hora_fin_operativa': 12, 'buffer_pips': 0.0}
  - 2022-2023 -> 2024: retorno -4.29%, drawdown -16.57%, params {'stop_loss_pips': 50, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 90, 'hora_fin_operativa': 14, 'buffer_pips': 3.0}
  - 2023-2024 -> 2025: retorno -5.45%, drawdown -6.95%, params {'stop_loss_pips': 40, 'take_profit_pips': 60, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 15, 'hora_fin_operativa': 12, 'buffer_pips': 1.0}
- RSI2 con tendencia: OOS medio -10.43%, score OOS -27.46, drawdown OOS -24.71%, folds positivos 0/3.
  - 2021-2022 -> 2023: retorno -2.25%, drawdown -10.52%, params {'stop_loss_pips': 40, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'ema_tendencia': 50, 'rsi_periodo': 5, 'umbral_largo': 10, 'umbral_corto': 90}
  - 2022-2023 -> 2024: retorno -18.38%, drawdown -24.56%, params {'stop_loss_pips': 40, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'ema_tendencia': 50, 'rsi_periodo': 5, 'umbral_largo': 10, 'umbral_corto': 90}
  - 2023-2024 -> 2025: retorno -10.65%, drawdown -39.06%, params {'stop_loss_pips': 20, 'take_profit_pips': 120, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'ema_tendencia': 50, 'rsi_periodo': 5, 'umbral_largo': 20, 'umbral_corto': 85}

## Mejor estrategia robusta hallada

- Estrategia: Bollinger + RSI
- Retorno medio OOS: 45.90%
- Drawdown medio OOS: -49.98%
- Folds positivos: 2/3

## Validacion final ampliada 2025

- Bollinger + RSI {'stop_loss_pips': 6, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}: retorno medio 10.94%, drawdown -54.94%, sharpe -0.45, profit factor 1.00.
- Ruptura de sesion {'stop_loss_pips': 40, 'take_profit_pips': 60, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 15, 'hora_fin_operativa': 12, 'buffer_pips': 1.0}: retorno medio -4.53%, drawdown -6.69%, sharpe -1.11, profit factor 0.83.
- RSI con niveles {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}: retorno medio -12.27%, drawdown -18.48%, sharpe -0.98, profit factor 0.75.

## Conclusiones operativas

- La mejor configuracion final ampliada fue `Bollinger + RSI` con parametros `{'stop_loss_pips': 6, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 3.0, 'rsi_periodo': 7}`.
- En los seis pares mayores de 2025 dio un retorno medio de 10.94% con drawdown medio de -54.94%.
- Aun asi, esto sigue siendo investigacion historica; no implica robustez futura ni garantiza beneficio real.