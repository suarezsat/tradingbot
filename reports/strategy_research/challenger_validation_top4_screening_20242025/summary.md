# Validacion dirigida de candidatos

- Fecha: 2026-04-24T09:49:46
- Pares: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, EURJPY
- Anos: 2024, 2025
- Spreads: 0.5, 1.0

## Spread 0.5 pip(s)

- Bollinger + RSI #6 {'stop_loss_pips': 15, 'take_profit_pips': 30, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 2.5, 'rsi_periodo': 21}: retorno medio 45.45%, drawdown -24.40%, sharpe 0.51, profit factor 1.03.
- RSI con niveles #4 {'stop_loss_pips': 15, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Nueva York', 'rsi_periodo': 21, 'nivel_sobrecompra': 80, 'nivel_sobreventa': 20}: retorno medio 12.12%, drawdown -20.85%, sharpe 0.29, profit factor 1.20.
- Filtro porcentual #3 {'stop_loss_pips': 25, 'take_profit_pips': 160, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Asiatica', 'lookback': 20, 'filtro_porcentual': 0.16}: retorno medio 1.13%, drawdown -3.23%, sharpe 0.06, profit factor 1.60.
- Filtro porcentual #5 {'stop_loss_pips': 40, 'take_profit_pips': 100, 'usar_trailing_stop': True, 'trailing_stop_pips': 15, 'session_label': 'Asiatica', 'lookback': 40, 'filtro_porcentual': 0.06}: retorno medio -0.51%, drawdown -5.66%, sharpe -0.29, profit factor 0.93.
- Ruptura de sesion #4 {'stop_loss_pips': 30, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 30, 'hora_fin_operativa': 14, 'buffer_pips': 0.0}: retorno medio -3.84%, drawdown -8.44%, sharpe -0.82, profit factor 0.89.
- Ruptura de sesion #2 {'stop_loss_pips': 40, 'take_profit_pips': 120, 'usar_trailing_stop': False, 'trailing_stop_pips': 15, 'session_label': 'Sin filtro', 'hora_inicio_utc': 13, 'minutos_rango': 90, 'hora_fin_operativa': 16, 'buffer_pips': 0.0}: retorno medio -4.32%, drawdown -17.00%, sharpe -0.43, profit factor 0.89.

## Spread 1.0 pip(s)

- RSI con niveles #4 {'stop_loss_pips': 15, 'take_profit_pips': 100, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Nueva York', 'rsi_periodo': 21, 'nivel_sobrecompra': 80, 'nivel_sobreventa': 20}: retorno medio 8.59%, drawdown -21.80%, sharpe 0.18, profit factor 1.15.
- Filtro porcentual #3 {'stop_loss_pips': 25, 'take_profit_pips': 160, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Asiatica', 'lookback': 20, 'filtro_porcentual': 0.16}: retorno medio 0.65%, drawdown -3.44%, sharpe -0.10, profit factor 1.41.
- Bollinger + RSI #6 {'stop_loss_pips': 15, 'take_profit_pips': 30, 'usar_trailing_stop': False, 'trailing_stop_pips': 12, 'session_label': 'Nueva York', 'bollinger_periodo': 40, 'desviaciones': 2.5, 'rsi_periodo': 21}: retorno medio -1.53%, drawdown -35.16%, sharpe -0.68, profit factor 0.93.
- Filtro porcentual #5 {'stop_loss_pips': 40, 'take_profit_pips': 100, 'usar_trailing_stop': True, 'trailing_stop_pips': 15, 'session_label': 'Asiatica', 'lookback': 40, 'filtro_porcentual': 0.06}: retorno medio -1.68%, drawdown -6.18%, sharpe -0.52, profit factor 0.87.
- Ruptura de sesion #2 {'stop_loss_pips': 40, 'take_profit_pips': 120, 'usar_trailing_stop': False, 'trailing_stop_pips': 15, 'session_label': 'Sin filtro', 'hora_inicio_utc': 13, 'minutos_rango': 90, 'hora_fin_operativa': 16, 'buffer_pips': 0.0}: retorno medio -5.86%, drawdown -17.54%, sharpe -0.54, profit factor 0.87.
- Ruptura de sesion #4 {'stop_loss_pips': 30, 'take_profit_pips': 30, 'usar_trailing_stop': True, 'trailing_stop_pips': 8, 'session_label': 'Sin filtro', 'hora_inicio_utc': 8, 'minutos_rango': 30, 'hora_fin_operativa': 14, 'buffer_pips': 0.0}: retorno medio -7.91%, drawdown -10.83%, sharpe -1.62, profit factor 0.78.
