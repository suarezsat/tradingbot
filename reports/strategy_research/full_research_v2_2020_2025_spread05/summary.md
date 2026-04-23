# Investigacion de estrategias Forex

- Fecha: 2026-04-24T00:30:42
- Spread supuesto: 0.5 pip(s)
- Pares nucleo: EURUSD, GBPUSD, USDJPY
- Pares validacion final: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD
- Anos screening: 2024, 2025
- Anos nucleo: 2020, 2021, 2022, 2023, 2024, 2025
- Anos validacion final: 2024, 2025
- Backtests ejecutados: 1260

## Protocolo

- Cribado inicial de todas las estrategias con combinaciones aleatorias y costes de spread.
- Busqueda profunda solo sobre las familias que mejor sobreviven.
- Seleccion con validacion walk-forward en ventanas de 2 anos de entrenamiento y 1 ano de prueba construidas automaticamente sobre los anos nucleo.
- Validacion final ampliada sobre los anos 2024, 2025 en 6 pares.

## Fuentes externas usadas

- Documentacion oficial de `backtesting.py` sobre `Backtest.optimize()` y el tratamiento de `spread`: https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html
- Hsu, Taylor y Wang (2016), sobre muchas reglas, control del data snooping y validacion fuera de muestra: https://www.sciencedirect.com/science/article/pii/S0022199616300472
- Neely y Weller (2003), sobre como la rentabilidad intradia desaparece facilmente al meter costes realistas: https://www.sciencedirect.com/science/article/pii/S0261560602001018
- Holmberg, Lonnbark y Lundstrom (2013), como justificacion para probar una familia ORB/rango inicial: https://www.sciencedirect.com/science/article/pii/S1544612312000438

## Top del cribado inicial

- RSI con niveles: score 10.64, retorno 4.25%, drawdown -22.82%.
- Filtro porcentual: score 7.76, retorno 13.51%, drawdown -12.32%.
- Bollinger + RSI: score 1.90, retorno 3.49%, drawdown -17.26%.
- Bollinger + RSI: score -4.42, retorno 3.87%, drawdown -22.27%.
- Ruptura de sesion: score -10.14, retorno -3.88%, drawdown -17.66%.
- RSI2 con tendencia: score -12.73, retorno -6.77%, drawdown -19.68%.
- Ruptura de sesion: score -15.87, retorno -6.00%, drawdown -8.92%.
- EMA + RSI tendencia: score -17.41, retorno -10.88%, drawdown -20.20%.
- EMA + RSI tendencia: score -20.91, retorno -8.99%, drawdown -21.35%.
- Filtro porcentual: score -25.85, retorno -12.36%, drawdown -24.91%.

## Top de la busqueda profunda

- Ruptura de sesion {'stop_loss_pips': 50, 'take_profit_pips': 120, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 14, 'buffer_pips': 1.0}: score -3.04, retorno -1.49%, drawdown -15.65%.
- Bollinger + RSI {'stop_loss_pips': 30, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 20, 'session_label': 'Londres', 'bollinger_periodo': 30, 'desviaciones': 1.5, 'rsi_periodo': 14}: score -4.47, retorno 7.22%, drawdown -24.15%.
- Bollinger + RSI {'stop_loss_pips': 20, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 30, 'desviaciones': 2.5, 'rsi_periodo': 14}: score -4.47, retorno 4.60%, drawdown -23.05%.
- Ruptura de sesion {'stop_loss_pips': 40, 'take_profit_pips': 80, 'usar_trailing_stop': True, 'trailing_stop_pips': 20, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 12, 'buffer_pips': 3.0}: score -4.96, retorno -3.34%, drawdown -11.60%.
- RSI con niveles {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}: score -7.03, retorno -5.27%, drawdown -18.51%.
- Ruptura de sesion {'stop_loss_pips': 20, 'take_profit_pips': 160, 'usar_trailing_stop': True, 'trailing_stop_pips': 15, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 60, 'hora_fin_operativa': 16, 'buffer_pips': 0.5}: score -8.85, retorno -5.14%, drawdown -17.65%.
- Ruptura de sesion {'stop_loss_pips': 25, 'take_profit_pips': 60, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 90, 'hora_fin_operativa': 14, 'buffer_pips': 0.5}: score -9.29, retorno -5.10%, drawdown -13.63%.
- Ruptura de sesion {'stop_loss_pips': 25, 'take_profit_pips': 120, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 45, 'hora_fin_operativa': 10, 'buffer_pips': 3.0}: score -10.90, retorno -5.49%, drawdown -11.99%.
- Ruptura de sesion {'stop_loss_pips': 15, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 11, 'buffer_pips': 1.5}: score -14.18, retorno -2.07%, drawdown -31.12%.
- RSI con niveles {'stop_loss_pips': 40, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Asiatica', 'rsi_periodo': 14, 'nivel_sobrecompra': 70, 'nivel_sobreventa': 25}: score -17.39, retorno -5.31%, drawdown -20.91%.

## Resultado walk-forward

- Bollinger + RSI: OOS medio 2.58%, score OOS -11.91, drawdown OOS -26.27%, folds positivos 3/4.
  - 2020-2021 -> 2022: retorno 18.06%, drawdown -24.96%, params {'stop_loss_pips': 30, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 20, 'session_label': 'Londres', 'bollinger_periodo': 30, 'desviaciones': 1.5, 'rsi_periodo': 14}
  - 2021-2022 -> 2023: retorno -19.57%, drawdown -34.97%, params {'stop_loss_pips': 30, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 20, 'session_label': 'Londres', 'bollinger_periodo': 30, 'desviaciones': 1.5, 'rsi_periodo': 14}
  - 2022-2023 -> 2024: retorno 5.26%, drawdown -19.95%, params {'stop_loss_pips': 20, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 30, 'desviaciones': 2.5, 'rsi_periodo': 14}
  - 2023-2024 -> 2025: retorno 6.57%, drawdown -25.18%, params {'stop_loss_pips': 20, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 30, 'desviaciones': 2.5, 'rsi_periodo': 14}
- RSI con niveles: OOS medio -5.86%, score OOS -7.12, drawdown OOS -18.90%, folds positivos 1/4.
  - 2020-2021 -> 2022: retorno -4.96%, drawdown -19.34%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
  - 2021-2022 -> 2023: retorno -13.79%, drawdown -19.86%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
  - 2022-2023 -> 2024: retorno 3.62%, drawdown -20.20%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
  - 2023-2024 -> 2025: retorno -8.29%, drawdown -16.20%, params {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}
- Filtro porcentual: OOS medio -10.05%, score OOS -64.96, drawdown OOS -20.85%, folds positivos 1/4.
  - 2020-2021 -> 2022: retorno -21.90%, drawdown -31.23%, params {'lookback': 30, 'filtro_porcentual': 0.08, 'stop_loss_pips': 20, 'take_profit_pips': 40, 'usar_trailing_stop': False, 'trailing_stop_pips': 15, 'session_label': 'Sin filtro'}
  - 2021-2022 -> 2023: retorno -21.87%, drawdown -36.36%, params {'stop_loss_pips': 12, 'take_profit_pips': 24, 'usar_trailing_stop': False, 'trailing_stop_pips': 15, 'session_label': 'Londres', 'lookback': 20, 'filtro_porcentual': 0.06}
  - 2022-2023 -> 2024: retorno 6.91%, drawdown -10.30%, params {'stop_loss_pips': 20, 'take_profit_pips': 160, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Londres', 'lookback': 90, 'filtro_porcentual': 0.2}
  - 2023-2024 -> 2025: retorno -3.33%, drawdown -5.52%, params {'stop_loss_pips': 30, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 30, 'session_label': 'Asiatica', 'lookback': 40, 'filtro_porcentual': 0.2}
- Ruptura de sesion: OOS medio -10.54%, score OOS -20.09, drawdown OOS -20.91%, folds positivos 0/4.
  - 2020-2021 -> 2022: retorno -0.60%, drawdown -17.13%, params {'stop_loss_pips': 50, 'take_profit_pips': 120, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 14, 'buffer_pips': 1.0}
  - 2021-2022 -> 2023: retorno -5.70%, drawdown -10.85%, params {'stop_loss_pips': 40, 'take_profit_pips': 80, 'usar_trailing_stop': True, 'trailing_stop_pips': 20, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 12, 'buffer_pips': 3.0}
  - 2022-2023 -> 2024: retorno -25.01%, drawdown -35.54%, params {'stop_loss_pips': 15, 'take_profit_pips': 60, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 11, 'buffer_pips': 1.5}
  - 2023-2024 -> 2025: retorno -10.85%, drawdown -20.12%, params {'stop_loss_pips': 50, 'take_profit_pips': 120, 'usar_trailing_stop': False, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 7, 'minutos_rango': 60, 'hora_fin_operativa': 14, 'buffer_pips': 1.0}

## Mejor estrategia robusta hallada

- Estrategia: Bollinger + RSI
- Retorno medio OOS: 2.58%
- Drawdown medio OOS: -26.27%
- Folds positivos: 3/4

## Validacion final ampliada 2024-2025

- Bollinger + RSI {'stop_loss_pips': 20, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 30, 'desviaciones': 2.5, 'rsi_periodo': 14}: retorno medio 9.34%, drawdown -20.18%, sharpe 0.31, profit factor 0.95.
- RSI con niveles {'stop_loss_pips': 6, 'take_profit_pips': 40, 'usar_trailing_stop': True, 'trailing_stop_pips': 12, 'session_label': 'Asiatica', 'rsi_periodo': 21, 'nivel_sobrecompra': 85, 'nivel_sobreventa': 20}: retorno medio -7.67%, drawdown -19.39%, sharpe -0.76, profit factor 0.84.
- Filtro porcentual {'lookback': 30, 'filtro_porcentual': 0.08, 'stop_loss_pips': 20, 'take_profit_pips': 40, 'usar_trailing_stop': False, 'trailing_stop_pips': 15, 'session_label': 'Sin filtro'}: retorno medio -16.05%, drawdown -25.77%, sharpe -1.20, profit factor 0.83.

## Conclusiones operativas

- La mejor configuracion final ampliada fue `Bollinger + RSI` con parametros `{'stop_loss_pips': 20, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 30, 'session_label': 'Nueva York', 'bollinger_periodo': 30, 'desviaciones': 2.5, 'rsi_periodo': 14}`.
- En los 6 pares y anos finales analizados dio un retorno medio de 9.34% con drawdown medio de -20.18%.
- Aun asi, esto sigue siendo investigacion historica; no implica robustez futura ni garantiza beneficio real.