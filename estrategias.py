"""Estrategias de trading y reglas comunes de gestion de riesgo."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover


def calcular_ema(valores, periodo: int):
    """Calcula una media movil exponencial."""
    return pd.Series(valores).ewm(span=periodo, adjust=False).mean().to_numpy()


def calcular_rsi(valores, periodo: int):
    """Calcula RSI usando suavizado exponencial."""
    serie = pd.Series(valores)
    delta = serie.diff()
    ganancias = delta.clip(lower=0)
    perdidas = -delta.clip(upper=0)

    media_ganancias = ganancias.ewm(
        alpha=1 / periodo, adjust=False, min_periods=periodo
    ).mean()
    media_perdidas = perdidas.ewm(
        alpha=1 / periodo, adjust=False, min_periods=periodo
    ).mean()

    fuerza_relativa = media_ganancias / media_perdidas.replace(0, np.nan)
    rsi = 100 - (100 / (1 + fuerza_relativa))
    return rsi.fillna(50).to_numpy()


def calcular_banda_superior(valores, periodo: int, desviaciones: float):
    """Devuelve la banda superior de Bollinger."""
    serie = pd.Series(valores)
    media = serie.rolling(periodo).mean()
    desviacion = serie.rolling(periodo).std(ddof=0)
    return (media + desviaciones * desviacion).to_numpy()


def calcular_banda_inferior(valores, periodo: int, desviaciones: float):
    """Devuelve la banda inferior de Bollinger."""
    serie = pd.Series(valores)
    media = serie.rolling(periodo).mean()
    desviacion = serie.rolling(periodo).std(ddof=0)
    return (media - desviaciones * desviacion).to_numpy()


def calcular_macd(valores, periodo_rapido: int, periodo_lento: int):
    """Calcula la linea MACD."""
    serie = pd.Series(valores)
    ema_rapida = serie.ewm(span=periodo_rapido, adjust=False).mean()
    ema_lenta = serie.ewm(span=periodo_lento, adjust=False).mean()
    return (ema_rapida - ema_lenta).to_numpy()


def calcular_macd_signal(valores, periodo_rapido: int, periodo_lento: int, periodo_signal: int):
    """Calcula la linea de senal de MACD."""
    macd = pd.Series(calcular_macd(valores, periodo_rapido, periodo_lento))
    return macd.ewm(span=periodo_signal, adjust=False).mean().to_numpy()


def calcular_donchian_superior(maximos, periodo: int):
    """Calcula el canal superior de Donchian excluyendo la vela actual."""
    serie = pd.Series(maximos)
    return serie.shift(1).rolling(periodo).max().to_numpy()


def calcular_donchian_inferior(minimos, periodo: int):
    """Calcula el canal inferior de Donchian excluyendo la vela actual."""
    serie = pd.Series(minimos)
    return serie.shift(1).rolling(periodo).min().to_numpy()


def calcular_stochastic_k(maximos, minimos, cierres, periodo: int):
    """Calcula el porcentaje K del oscilador estocastico."""
    max_serie = pd.Series(maximos)
    min_serie = pd.Series(minimos)
    close_serie = pd.Series(cierres)
    min_rodante = min_serie.rolling(periodo).min()
    max_rodante = max_serie.rolling(periodo).max()
    rango = (max_rodante - min_rodante).replace(0, np.nan)
    k = 100 * ((close_serie - min_rodante) / rango)
    return k.fillna(50).to_numpy()


def calcular_stochastic_d(maximos, minimos, cierres, periodo_k: int, periodo_d: int):
    """Calcula el porcentaje D del oscilador estocastico."""
    k = pd.Series(calcular_stochastic_k(maximos, minimos, cierres, periodo_k))
    return k.rolling(periodo_d).mean().fillna(50).to_numpy()


def calcular_roc(valores, periodo: int):
    """Calcula el Rate of Change porcentual."""
    serie = pd.Series(valores, dtype=float)
    roc = ((serie / serie.shift(periodo)) - 1.0) * 100.0
    return roc.fillna(0.0).to_numpy()


@dataclass(frozen=True)
class ParametroUI:
    """Describe un control de la interfaz asociado a una estrategia."""

    clave: str
    etiqueta: str
    tipo: str
    valor_min: float
    valor_max: float
    valor_defecto: float
    paso: float
    ayuda: str


class EstrategiaBaseForex(Strategy):
    """Clase base con posicionamiento, filtros horarios y trailing stop."""

    stop_loss_pips = 20
    take_profit_pips = 40
    risk_per_trade = 1.0
    max_open_trades = 1
    session_start = -1
    session_end = -1
    usar_trailing_stop = False
    trailing_stop_pips = 15
    pip_size = 0.0001
    leverage = 30.0

    def _senal_compra(self) -> bool:
        raise NotImplementedError

    def _senal_venta(self) -> bool:
        raise NotImplementedError

    def _esta_en_sesion(self) -> bool:
        """Filtra por horario usando la hora del CSV asumida como UTC."""
        if self.session_start < 0 or self.session_end < 0:
            return True

        marca_tiempo = pd.Timestamp(self.data.index[-1])
        hora_decimal = marca_tiempo.hour + (marca_tiempo.minute / 60)
        return self.session_start <= hora_decimal < self.session_end

    def _tiene_opuestas_abiertas(self, direccion: str) -> bool:
        if direccion == "long":
            return any(trade.is_short for trade in self.trades)
        return any(trade.is_long for trade in self.trades)

    def _ya_hay_direccion_abierta(self, direccion: str) -> bool:
        if direccion == "long":
            return any(trade.is_long for trade in self.trades)
        return any(trade.is_short for trade in self.trades)

    def _puede_abrir_nueva_operacion(self, direccion: str) -> bool:
        """Permite reversals pero limita entradas repetidas cuando se alcanza el maximo."""
        max_operaciones = max(int(self.max_open_trades), 1)
        total_abiertas = len(self.trades)

        if total_abiertas < max_operaciones:
            return True

        return self._tiene_opuestas_abiertas(direccion)

    def _calcular_tamano_posicion(self) -> int:
        """Calcula el tamano segun riesgo y apalancamiento maximo."""
        precio_actual = float(self.data.Close[-1])
        distancia_stop = float(self.stop_loss_pips) * float(self.pip_size)
        riesgo_monetario = float(self.equity) * (float(self.risk_per_trade) / 100)

        if precio_actual <= 0 or distancia_stop <= 0 or riesgo_monetario <= 0:
            return 0

        tamano_por_riesgo = riesgo_monetario / distancia_stop
        margen_requerido = 1 / max(float(self.leverage), 1.0)
        tamano_maximo = float(self.equity) / max(precio_actual * margen_requerido, 1e-9)

        return max(int(min(tamano_por_riesgo, tamano_maximo)), 1)

    def _actualizar_trailing_stop(self):
        """Mueve el stop a favor cuando el trailing esta activado."""
        if not self.usar_trailing_stop:
            return

        distancia = float(self.trailing_stop_pips) * float(self.pip_size)
        if distancia <= 0:
            return

        precio_actual = float(self.data.Close[-1])

        for trade in self.trades:
            if trade.is_long:
                nuevo_stop = precio_actual - distancia
                if trade.sl is None or nuevo_stop > trade.sl:
                    trade.sl = nuevo_stop
            else:
                nuevo_stop = precio_actual + distancia
                if trade.sl is None or nuevo_stop < trade.sl:
                    trade.sl = nuevo_stop

    def _abrir_operacion(self, direccion: str):
        """Abre una orden con stop, take profit y tamano calculado."""
        tamano = self._calcular_tamano_posicion()
        if tamano <= 0:
            return

        precio_actual = float(self.data.Close[-1])
        distancia_stop = float(self.stop_loss_pips) * float(self.pip_size)
        distancia_objetivo = float(self.take_profit_pips) * float(self.pip_size)

        if direccion == "long":
            self.buy(
                size=tamano,
                sl=precio_actual - distancia_stop,
                tp=precio_actual + distancia_objetivo,
            )
        else:
            self.sell(
                size=tamano,
                sl=precio_actual + distancia_stop,
                tp=precio_actual - distancia_objetivo,
            )

    def next(self):
        """Ejecuta en cada vela las reglas comunes y la logica especifica."""
        self._actualizar_trailing_stop()

        if not self._esta_en_sesion():
            return

        if self._senal_compra():
            if self._ya_hay_direccion_abierta("long") and int(self.max_open_trades) <= 1:
                return
            if self._puede_abrir_nueva_operacion("long"):
                self._abrir_operacion("long")
        elif self._senal_venta():
            if self._ya_hay_direccion_abierta("short") and int(self.max_open_trades) <= 1:
                return
            if self._puede_abrir_nueva_operacion("short"):
                self._abrir_operacion("short")


class EstrategiaCruceEMAs(EstrategiaBaseForex):
    """Compra y vende con cruce de medias moviles exponenciales."""

    ema_rapida = 10
    ema_lenta = 50

    def init(self):
        self.ema_fast = self.I(calcular_ema, self.data.Close, int(self.ema_rapida))
        self.ema_slow = self.I(calcular_ema, self.data.Close, int(self.ema_lenta))

    def _senal_compra(self) -> bool:
        return crossover(self.ema_fast, self.ema_slow)

    def _senal_venta(self) -> bool:
        return crossover(self.ema_slow, self.ema_fast)


class EstrategiaRSI(EstrategiaBaseForex):
    """Busca giros cuando el RSI sale de sobreventa o sobrecompra."""

    rsi_periodo = 14
    nivel_sobrecompra = 70
    nivel_sobreventa = 30

    def init(self):
        self.rsi = self.I(calcular_rsi, self.data.Close, int(self.rsi_periodo))

    def _senal_compra(self) -> bool:
        return self.rsi[-2] < float(self.nivel_sobreventa) <= self.rsi[-1]

    def _senal_venta(self) -> bool:
        return self.rsi[-2] > float(self.nivel_sobrecompra) >= self.rsi[-1]


class EstrategiaBollingerRSI(EstrategiaBaseForex):
    """Combina rebotes en bandas de Bollinger con confirmacion de RSI."""

    bollinger_periodo = 20
    desviaciones = 2.0
    rsi_periodo = 14

    def init(self):
        self.banda_superior = self.I(
            calcular_banda_superior,
            self.data.Close,
            int(self.bollinger_periodo),
            float(self.desviaciones),
        )
        self.banda_inferior = self.I(
            calcular_banda_inferior,
            self.data.Close,
            int(self.bollinger_periodo),
            float(self.desviaciones),
        )
        self.rsi = self.I(calcular_rsi, self.data.Close, int(self.rsi_periodo))

    def _senal_compra(self) -> bool:
        return bool(self.data.Low[-1] <= self.banda_inferior[-1] and self.rsi[-1] < 40)

    def _senal_venta(self) -> bool:
        return bool(self.data.High[-1] >= self.banda_superior[-1] and self.rsi[-1] > 60)


class EstrategiaMACD(EstrategiaBaseForex):
    """Opera con cruces entre MACD y su linea de senal."""

    macd_rapido = 12
    macd_lento = 26
    macd_signal = 9

    def init(self):
        self.macd = self.I(
            calcular_macd,
            self.data.Close,
            int(self.macd_rapido),
            int(self.macd_lento),
        )
        self.signal = self.I(
            calcular_macd_signal,
            self.data.Close,
            int(self.macd_rapido),
            int(self.macd_lento),
            int(self.macd_signal),
        )

    def _senal_compra(self) -> bool:
        return crossover(self.macd, self.signal)

    def _senal_venta(self) -> bool:
        return crossover(self.signal, self.macd)


class EstrategiaDonchian(EstrategiaBaseForex):
    """Busca rupturas del maximo o minimo de las ultimas velas."""

    donchian_periodo = 20

    def init(self):
        self.canal_superior = self.I(
            calcular_donchian_superior,
            self.data.High,
            int(self.donchian_periodo),
        )
        self.canal_inferior = self.I(
            calcular_donchian_inferior,
            self.data.Low,
            int(self.donchian_periodo),
        )

    def _senal_compra(self) -> bool:
        return bool(
            not np.isnan(self.canal_superior[-1]) and self.data.Close[-1] > self.canal_superior[-1]
        )

    def _senal_venta(self) -> bool:
        return bool(
            not np.isnan(self.canal_inferior[-1]) and self.data.Close[-1] < self.canal_inferior[-1]
        )


class EstrategiaEMARSI(EstrategiaBaseForex):
    """Combina direccion de EMAs con confirmacion de RSI."""

    ema_rapida = 20
    ema_lenta = 100
    rsi_periodo = 14
    rsi_largo = 55
    rsi_corto = 45

    def init(self):
        self.ema_fast = self.I(calcular_ema, self.data.Close, int(self.ema_rapida))
        self.ema_slow = self.I(calcular_ema, self.data.Close, int(self.ema_lenta))
        self.rsi = self.I(calcular_rsi, self.data.Close, int(self.rsi_periodo))

    def _senal_compra(self) -> bool:
        return bool(
            self.ema_fast[-1] > self.ema_slow[-1]
            and self.rsi[-2] < float(self.rsi_largo) <= self.rsi[-1]
        )

    def _senal_venta(self) -> bool:
        return bool(
            self.ema_fast[-1] < self.ema_slow[-1]
            and self.rsi[-2] > float(self.rsi_corto) >= self.rsi[-1]
        )


class EstrategiaEstocastico(EstrategiaBaseForex):
    """Usa el cruce del estocastico en zonas extremas."""

    stoch_k = 14
    stoch_d = 3
    nivel_sobrecompra = 80
    nivel_sobreventa = 20

    def init(self):
        self.k = self.I(
            calcular_stochastic_k,
            self.data.High,
            self.data.Low,
            self.data.Close,
            int(self.stoch_k),
        )
        self.d = self.I(
            calcular_stochastic_d,
            self.data.High,
            self.data.Low,
            self.data.Close,
            int(self.stoch_k),
            int(self.stoch_d),
        )

    def _senal_compra(self) -> bool:
        return bool(
            self.k[-2] < self.d[-2]
            and self.k[-1] > self.d[-1]
            and self.k[-1] < float(self.nivel_sobreventa)
        )

    def _senal_venta(self) -> bool:
        return bool(
            self.k[-2] > self.d[-2]
            and self.k[-1] < self.d[-1]
            and self.k[-1] > float(self.nivel_sobrecompra)
        )


class EstrategiaDonchianEMA(EstrategiaBaseForex):
    """Ruptura de Donchian filtrada por una EMA tendencial."""

    donchian_periodo = 30
    ema_tendencia = 200

    def init(self):
        self.canal_superior = self.I(
            calcular_donchian_superior,
            self.data.High,
            int(self.donchian_periodo),
        )
        self.canal_inferior = self.I(
            calcular_donchian_inferior,
            self.data.Low,
            int(self.donchian_periodo),
        )
        self.ema = self.I(calcular_ema, self.data.Close, int(self.ema_tendencia))

    def _senal_compra(self) -> bool:
        return bool(
            not np.isnan(self.canal_superior[-1])
            and self.data.Close[-1] > self.canal_superior[-1]
            and self.data.Close[-1] > self.ema[-1]
        )

    def _senal_venta(self) -> bool:
        return bool(
            not np.isnan(self.canal_inferior[-1])
            and self.data.Close[-1] < self.canal_inferior[-1]
            and self.data.Close[-1] < self.ema[-1]
        )


class EstrategiaRSI2Tendencia(EstrategiaBaseForex):
    """Busca micro retrocesos con RSI corto dentro de una tendencia mayor."""

    ema_tendencia = 200
    rsi_periodo = 2
    umbral_largo = 15
    umbral_corto = 85

    def init(self):
        self.ema = self.I(calcular_ema, self.data.Close, int(self.ema_tendencia))
        self.rsi = self.I(calcular_rsi, self.data.Close, int(self.rsi_periodo))

    def _senal_compra(self) -> bool:
        return bool(
            self.data.Close[-1] > self.ema[-1]
            and self.rsi[-2] <= float(self.umbral_largo) < self.rsi[-1]
        )

    def _senal_venta(self) -> bool:
        return bool(
            self.data.Close[-1] < self.ema[-1]
            and self.rsi[-2] >= float(self.umbral_corto) > self.rsi[-1]
        )


class EstrategiaRupturaSesion(EstrategiaBaseForex):
    """Opera la ruptura del rango inicial de una sesion intradia."""

    hora_inicio_utc = 7
    minutos_rango = 60
    hora_fin_operativa = 12
    buffer_pips = 1.0

    def init(self):
        self._fecha_actual = None
        self._maximo_rango = np.nan
        self._minimo_rango = np.nan
        self._operacion_lanzada = False

    def _reiniciar_dia(self, fecha):
        self._fecha_actual = fecha
        self._maximo_rango = np.nan
        self._minimo_rango = np.nan
        self._operacion_lanzada = False

    def next(self):
        """Construye el rango al inicio de la sesion y opera solo la primera ruptura."""
        self._actualizar_trailing_stop()

        marca_tiempo = pd.Timestamp(self.data.index[-1])
        fecha = marca_tiempo.date()
        if fecha != self._fecha_actual:
            self._reiniciar_dia(fecha)

        if not self._esta_en_sesion():
            return

        minuto_actual = marca_tiempo.hour * 60 + marca_tiempo.minute
        minuto_inicio = int(self.hora_inicio_utc) * 60
        minuto_fin_rango = minuto_inicio + int(self.minutos_rango)
        minuto_fin_operativa = int(self.hora_fin_operativa) * 60

        if minuto_actual < minuto_inicio or minuto_actual >= minuto_fin_operativa:
            return

        if minuto_inicio <= minuto_actual < minuto_fin_rango:
            maximo = float(self.data.High[-1])
            minimo = float(self.data.Low[-1])
            self._maximo_rango = (
                maximo if np.isnan(self._maximo_rango) else max(self._maximo_rango, maximo)
            )
            self._minimo_rango = (
                minimo if np.isnan(self._minimo_rango) else min(self._minimo_rango, minimo)
            )
            return

        if self._operacion_lanzada or np.isnan(self._maximo_rango) or np.isnan(self._minimo_rango):
            return

        buffer = float(self.buffer_pips) * float(self.pip_size)
        cierre = float(self.data.Close[-1])

        if cierre > self._maximo_rango + buffer:
            if self._ya_hay_direccion_abierta("long") and int(self.max_open_trades) <= 1:
                return
            if self._puede_abrir_nueva_operacion("long"):
                self._abrir_operacion("long")
                self._operacion_lanzada = True
        elif cierre < self._minimo_rango - buffer:
            if self._ya_hay_direccion_abierta("short") and int(self.max_open_trades) <= 1:
                return
            if self._puede_abrir_nueva_operacion("short"):
                self._abrir_operacion("short")
                self._operacion_lanzada = True


class EstrategiaFiltroPorcentual(EstrategiaBaseForex):
    """Extiende el breakout clasico exigiendo una ruptura porcentual minima."""

    lookback = 30
    filtro_porcentual = 0.08

    def init(self):
        self.canal_superior = self.I(
            calcular_donchian_superior,
            self.data.High,
            int(self.lookback),
        )
        self.canal_inferior = self.I(
            calcular_donchian_inferior,
            self.data.Low,
            int(self.lookback),
        )

    def _senal_compra(self) -> bool:
        if np.isnan(self.canal_superior[-1]):
            return False
        umbral = self.canal_superior[-1] * (1.0 + float(self.filtro_porcentual) / 100.0)
        return bool(self.data.Close[-1] > umbral)

    def _senal_venta(self) -> bool:
        if np.isnan(self.canal_inferior[-1]):
            return False
        umbral = self.canal_inferior[-1] * (1.0 - float(self.filtro_porcentual) / 100.0)
        return bool(self.data.Close[-1] < umbral)


class EstrategiaMomentumROC(EstrategiaBaseForex):
    """Opera continuidad cuando el momentum supera un umbral dentro de tendencia."""

    roc_periodo = 30
    umbral_roc = 0.12
    ema_tendencia = 200

    def init(self):
        self.roc = self.I(calcular_roc, self.data.Close, int(self.roc_periodo))
        self.ema = self.I(calcular_ema, self.data.Close, int(self.ema_tendencia))

    def _senal_compra(self) -> bool:
        umbral = float(self.umbral_roc)
        return bool(
            self.data.Close[-1] > self.ema[-1]
            and self.roc[-2] <= umbral < self.roc[-1]
        )

    def _senal_venta(self) -> bool:
        umbral = -float(self.umbral_roc)
        return bool(
            self.data.Close[-1] < self.ema[-1]
            and self.roc[-2] >= umbral > self.roc[-1]
        )


CONFIGURACION_ESTRATEGIAS = {
    "Cruce de Medias Moviles": {
        "clase": EstrategiaCruceEMAs,
        "descripcion": "Compra cuando la EMA rapida cruza al alza y vende al cruce bajista.",
        "parametros": [
            ParametroUI(
                clave="ema_rapida",
                etiqueta="Periodo EMA rapida",
                tipo="int",
                valor_min=2,
                valor_max=100,
                valor_defecto=10,
                paso=1,
                ayuda="Numero de velas usado para la EMA rapida.",
            ),
            ParametroUI(
                clave="ema_lenta",
                etiqueta="Periodo EMA lenta",
                tipo="int",
                valor_min=5,
                valor_max=300,
                valor_defecto=50,
                paso=1,
                ayuda="Numero de velas usado para la EMA lenta.",
            ),
        ],
    },
    "RSI con niveles": {
        "clase": EstrategiaRSI,
        "descripcion": "Busca compras al salir de sobreventa y ventas al salir de sobrecompra.",
        "parametros": [
            ParametroUI(
                clave="rsi_periodo",
                etiqueta="Periodo RSI",
                tipo="int",
                valor_min=2,
                valor_max=100,
                valor_defecto=14,
                paso=1,
                ayuda="Periodo del indicador RSI.",
            ),
            ParametroUI(
                clave="nivel_sobrecompra",
                etiqueta="Nivel de sobrecompra",
                tipo="int",
                valor_min=50,
                valor_max=95,
                valor_defecto=70,
                paso=1,
                ayuda="Nivel a partir del cual se considera sobrecompra.",
            ),
            ParametroUI(
                clave="nivel_sobreventa",
                etiqueta="Nivel de sobreventa",
                tipo="int",
                valor_min=5,
                valor_max=50,
                valor_defecto=30,
                paso=1,
                ayuda="Nivel por debajo del cual se considera sobreventa.",
            ),
        ],
    },
    "Bollinger + RSI": {
        "clase": EstrategiaBollingerRSI,
        "descripcion": "Combina toque de bandas de Bollinger con filtro de RSI.",
        "parametros": [
            ParametroUI(
                clave="bollinger_periodo",
                etiqueta="Periodo Bollinger",
                tipo="int",
                valor_min=5,
                valor_max=200,
                valor_defecto=20,
                paso=1,
                ayuda="Numero de velas usadas para la media de Bollinger.",
            ),
            ParametroUI(
                clave="desviaciones",
                etiqueta="Desviaciones estandar",
                tipo="float",
                valor_min=1.0,
                valor_max=4.0,
                valor_defecto=2.0,
                paso=0.1,
                ayuda="Ancho de las bandas de Bollinger.",
            ),
            ParametroUI(
                clave="rsi_periodo",
                etiqueta="Periodo RSI",
                tipo="int",
                valor_min=2,
                valor_max=100,
                valor_defecto=14,
                paso=1,
                ayuda="Periodo del RSI usado como confirmacion.",
            ),
        ],
    },
    "MACD clasico": {
        "clase": EstrategiaMACD,
        "descripcion": "Compra cuando MACD cruza arriba de la senal y vende al cruce bajista.",
        "parametros": [
            ParametroUI(
                clave="macd_rapido",
                etiqueta="Periodo MACD rapido",
                tipo="int",
                valor_min=2,
                valor_max=50,
                valor_defecto=12,
                paso=1,
                ayuda="Periodo de la EMA rapida del MACD.",
            ),
            ParametroUI(
                clave="macd_lento",
                etiqueta="Periodo MACD lento",
                tipo="int",
                valor_min=5,
                valor_max=100,
                valor_defecto=26,
                paso=1,
                ayuda="Periodo de la EMA lenta del MACD.",
            ),
            ParametroUI(
                clave="macd_signal",
                etiqueta="Periodo linea de senal",
                tipo="int",
                valor_min=2,
                valor_max=50,
                valor_defecto=9,
                paso=1,
                ayuda="Suavizado de la linea de senal.",
            ),
        ],
    },
    "Donchian Breakout": {
        "clase": EstrategiaDonchian,
        "descripcion": "Entra cuando el precio rompe el maximo o minimo del canal de Donchian.",
        "parametros": [
            ParametroUI(
                clave="donchian_periodo",
                etiqueta="Periodo Donchian",
                tipo="int",
                valor_min=5,
                valor_max=200,
                valor_defecto=20,
                paso=1,
                ayuda="Numero de velas usadas para calcular el canal.",
            ),
        ],
    },
    "EMA + RSI tendencia": {
        "clase": EstrategiaEMARSI,
        "descripcion": "Filtra la tendencia con EMAs y confirma la entrada con cruces de RSI.",
        "parametros": [
            ParametroUI(
                clave="ema_rapida",
                etiqueta="Periodo EMA rapida",
                tipo="int",
                valor_min=2,
                valor_max=100,
                valor_defecto=20,
                paso=1,
                ayuda="Periodo de la EMA rapida del filtro tendencial.",
            ),
            ParametroUI(
                clave="ema_lenta",
                etiqueta="Periodo EMA lenta",
                tipo="int",
                valor_min=5,
                valor_max=300,
                valor_defecto=100,
                paso=1,
                ayuda="Periodo de la EMA lenta del filtro tendencial.",
            ),
            ParametroUI(
                clave="rsi_periodo",
                etiqueta="Periodo RSI",
                tipo="int",
                valor_min=2,
                valor_max=100,
                valor_defecto=14,
                paso=1,
                ayuda="Periodo del RSI de confirmacion.",
            ),
            ParametroUI(
                clave="rsi_largo",
                etiqueta="Nivel RSI para largos",
                tipo="int",
                valor_min=40,
                valor_max=80,
                valor_defecto=55,
                paso=1,
                ayuda="Nivel que debe superar el RSI para compras.",
            ),
            ParametroUI(
                clave="rsi_corto",
                etiqueta="Nivel RSI para cortos",
                tipo="int",
                valor_min=20,
                valor_max=60,
                valor_defecto=45,
                paso=1,
                ayuda="Nivel que debe perder el RSI para ventas.",
            ),
        ],
    },
    "Estocastico extremo": {
        "clase": EstrategiaEstocastico,
        "descripcion": "Busca cruces del estocastico dentro de zonas de sobrecompra o sobreventa.",
        "parametros": [
            ParametroUI(
                clave="stoch_k",
                etiqueta="Periodo %K",
                tipo="int",
                valor_min=3,
                valor_max=50,
                valor_defecto=14,
                paso=1,
                ayuda="Periodo principal del estocastico.",
            ),
            ParametroUI(
                clave="stoch_d",
                etiqueta="Periodo %D",
                tipo="int",
                valor_min=2,
                valor_max=20,
                valor_defecto=3,
                paso=1,
                ayuda="Media de suavizado de la linea %D.",
            ),
            ParametroUI(
                clave="nivel_sobrecompra",
                etiqueta="Nivel de sobrecompra",
                tipo="int",
                valor_min=50,
                valor_max=95,
                valor_defecto=80,
                paso=1,
                ayuda="Nivel alto de referencia para ventas.",
            ),
            ParametroUI(
                clave="nivel_sobreventa",
                etiqueta="Nivel de sobreventa",
                tipo="int",
                valor_min=5,
                valor_max=50,
                valor_defecto=20,
                paso=1,
                ayuda="Nivel bajo de referencia para compras.",
            ),
        ],
    },
    "Donchian + EMA": {
        "clase": EstrategiaDonchianEMA,
        "descripcion": "Ruptura del canal de Donchian a favor de una EMA de tendencia.",
        "parametros": [
            ParametroUI(
                clave="donchian_periodo",
                etiqueta="Periodo Donchian",
                tipo="int",
                valor_min=5,
                valor_max=250,
                valor_defecto=30,
                paso=1,
                ayuda="Numero de velas usadas para calcular la ruptura.",
            ),
            ParametroUI(
                clave="ema_tendencia",
                etiqueta="Periodo EMA tendencia",
                tipo="int",
                valor_min=20,
                valor_max=400,
                valor_defecto=200,
                paso=1,
                ayuda="EMA usada como filtro de fondo tendencial.",
            ),
        ],
    },
    "RSI2 con tendencia": {
        "clase": EstrategiaRSI2Tendencia,
        "descripcion": "Mean reversion corto dentro de una tendencia mayor filtrada por EMA.",
        "parametros": [
            ParametroUI(
                clave="ema_tendencia",
                etiqueta="Periodo EMA tendencia",
                tipo="int",
                valor_min=20,
                valor_max=400,
                valor_defecto=200,
                paso=1,
                ayuda="EMA que define el sesgo principal del mercado.",
            ),
            ParametroUI(
                clave="rsi_periodo",
                etiqueta="Periodo RSI",
                tipo="int",
                valor_min=2,
                valor_max=10,
                valor_defecto=2,
                paso=1,
                ayuda="RSI corto para detectar retrocesos intradia.",
            ),
            ParametroUI(
                clave="umbral_largo",
                etiqueta="Umbral RSI largos",
                tipo="int",
                valor_min=2,
                valor_max=40,
                valor_defecto=15,
                paso=1,
                ayuda="Nivel que el RSI debe recuperar al alza para comprar.",
            ),
            ParametroUI(
                clave="umbral_corto",
                etiqueta="Umbral RSI cortos",
                tipo="int",
                valor_min=60,
                valor_max=98,
                valor_defecto=85,
                paso=1,
                ayuda="Nivel que el RSI debe perder a la baja para vender.",
            ),
        ],
    },
    "Ruptura de sesion": {
        "clase": EstrategiaRupturaSesion,
        "descripcion": "Opera la primera ruptura del rango inicial de una sesion intradia.",
        "parametros": [
            ParametroUI(
                clave="hora_inicio_utc",
                etiqueta="Hora inicio UTC",
                tipo="int",
                valor_min=0,
                valor_max=20,
                valor_defecto=7,
                paso=1,
                ayuda="Hora UTC a partir de la que se empieza a construir el rango.",
            ),
            ParametroUI(
                clave="minutos_rango",
                etiqueta="Minutos del rango",
                tipo="int",
                valor_min=15,
                valor_max=180,
                valor_defecto=60,
                paso=5,
                ayuda="Duracion del rango inicial antes de buscar la ruptura.",
            ),
            ParametroUI(
                clave="hora_fin_operativa",
                etiqueta="Hora fin operativa UTC",
                tipo="int",
                valor_min=1,
                valor_max=23,
                valor_defecto=12,
                paso=1,
                ayuda="Hora limite hasta la que se permiten entradas ese dia.",
            ),
            ParametroUI(
                clave="buffer_pips",
                etiqueta="Buffer de ruptura (pips)",
                tipo="float",
                valor_min=0.0,
                valor_max=10.0,
                valor_defecto=1.0,
                paso=0.5,
                ayuda="Margen adicional para evitar rupturas demasiado justas.",
            ),
        ],
    },
    "Filtro porcentual": {
        "clase": EstrategiaFiltroPorcentual,
        "descripcion": "Ruptura de maximos/minimos previos solo si supera un filtro porcentual minimo.",
        "parametros": [
            ParametroUI(
                clave="lookback",
                etiqueta="Lookback de extremos",
                tipo="int",
                valor_min=5,
                valor_max=240,
                valor_defecto=30,
                paso=1,
                ayuda="Numero de velas para definir el maximo y minimo previos.",
            ),
            ParametroUI(
                clave="filtro_porcentual",
                etiqueta="Filtro porcentual (%)",
                tipo="float",
                valor_min=0.01,
                valor_max=1.0,
                valor_defecto=0.08,
                paso=0.01,
                ayuda="Porcentaje adicional que debe romper el precio para activar la entrada.",
            ),
        ],
    },
    "Momentum ROC": {
        "clase": EstrategiaMomentumROC,
        "descripcion": "Sigue continuidad direccional cuando el ROC cruza un umbral dentro de tendencia.",
        "parametros": [
            ParametroUI(
                clave="roc_periodo",
                etiqueta="Periodo ROC",
                tipo="int",
                valor_min=5,
                valor_max=240,
                valor_defecto=30,
                paso=1,
                ayuda="Numero de velas usadas para medir el momentum porcentual.",
            ),
            ParametroUI(
                clave="umbral_roc",
                etiqueta="Umbral ROC (%)",
                tipo="float",
                valor_min=0.01,
                valor_max=1.0,
                valor_defecto=0.12,
                paso=0.01,
                ayuda="Umbral minimo de momentum para activar la senal.",
            ),
            ParametroUI(
                clave="ema_tendencia",
                etiqueta="Periodo EMA tendencia",
                tipo="int",
                valor_min=20,
                valor_max=400,
                valor_defecto=200,
                paso=1,
                ayuda="EMA usada como filtro de sesgo principal.",
            ),
        ],
    },
}


ESTRATEGIAS_CLASICAS = [
    "Cruce de Medias Moviles",
    "RSI con niveles",
    "Bollinger + RSI",
]
