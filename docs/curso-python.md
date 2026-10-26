# Curso de Python con el sistema de Transportes Hidalgo

Este curso enseña Python **desde cero** usando el código real del sistema de gestión de flota.
Cada lección explica un tema, muestra dónde se usa en el sistema y propone ejercicios para hacer
en la consola de Python. Las soluciones están al final.

<!-- solo-md:inicio -->
> En VS Code: `Ctrl+Shift+V` para ver este archivo formateado. Versión Word en el escritorio
> y en `docs/word/Curso-Python.docx`.
<!-- solo-md:fin -->

---

## Índice

**Antes de empezar**

0. [Cómo usar este curso](#0-cómo-usar-este-curso)

**Parte 1 — Fundamentos**

1. [La consola de Python](#1-la-consola-de-python)
2. [Variables y tipos de datos](#2-variables-y-tipos-de-datos)
3. [Textos (strings)](#3-textos-strings)
4. [Listas y diccionarios](#4-listas-y-diccionarios)
5. [Decisiones y repeticiones](#5-decisiones-y-repeticiones)
6. [Funciones](#6-funciones)

**Parte 2 — Programar con objetos**

7. [Clases y dataclasses](#7-clases-y-dataclasses)
8. [Enumeraciones y propiedades](#8-enumeraciones-y-propiedades)
9. [Errores y excepciones](#9-errores-y-excepciones)
10. [Objetos de valor y métodos especiales](#10-objetos-de-valor-y-métodos-especiales)
11. [Objetos que contienen objetos](#11-objetos-que-contienen-objetos)

**Parte 3 — Organizar un programa grande**

12. [Módulos, paquetes e imports](#12-módulos-paquetes-e-imports)
13. [Tipos, interfaces y casos de uso](#13-tipos-interfaces-y-casos-de-uso)
14. [`with`, funciones como valores y eventos](#14-with-funciones-como-valores-y-eventos)
15. [Generadores](#15-generadores)

**Parte 4 — Las librerías del sistema**

16. [Pydantic y FastAPI](#16-pydantic-y-fastapi)
17. [SQLAlchemy y la base de datos](#17-sqlalchemy-y-la-base-de-datos)
18. [Tests con pytest](#18-tests-con-pytest)

**Parte 5 — Práctica final**

19. [Proyecto guiado: agregar una funcionalidad](#19-proyecto-guiado-agregar-una-funcionalidad)

**Anexos**

- [Soluciones de los ejercicios](#soluciones-de-los-ejercicios)
- [Hoja de referencia rápida](#hoja-de-referencia-rápida)
- [Cómo seguir aprendiendo](#cómo-seguir-aprendiendo)

---

## 0. Cómo usar este curso

**Ritmo sugerido:** una lección por día, de 30 a 60 minutos. Las lecciones 1 a 6 son la base:
no las saltees aunque parezcan fáciles.

**En cada lección:**

1. Leé la explicación.
2. Mirá el ejemplo del sistema (si podés, abrí el archivo en VS Code).
3. Escribí vos los ejemplos en la consola: **escribirlos** enseña más que leerlos.
4. Hacé los ejercicios antes de mirar las soluciones.

**Cuando algo da error:** es normal y es parte de aprender. Leé el mensaje de abajo hacia arriba:
la última línea dice qué pasó (`NameError`, `TypeError`…) y las de arriba, dónde.

---

# Parte 1 — Fundamentos

## 1. La consola de Python

**Vas a aprender:** a abrir Python, escribir instrucciones y ver el resultado al instante.

Abrí una terminal en VS Code (`Ctrl+ñ`) dentro de la carpeta del proyecto y escribí:

```powershell
uv run python
```

(Si `uv` no funciona: `.venv\Scripts\python.exe`.) Vas a ver el símbolo `>>>`: Python espera una
instrucción. Esta "consola interactiva" se llama **REPL** (*Read-Eval-Print Loop*: lee, evalúa,
muestra, repite).

```python
>>> 2 + 3
5
>>> print("Transportes Hidalgo")
Transportes Hidalgo
>>> # esto es un comentario: Python lo ignora
```

- `print(...)` muestra algo en pantalla.
- Todo lo que sigue a `#` es un **comentario**: sirve para explicar el código a las personas.
- Para salir de la consola: `exit()`.

**Programas en archivos.** Un programa es un archivo `.py` con instrucciones que se ejecutan de
arriba hacia abajo. Por ejemplo, el comando `flota datos-demo` ejecuta la función `datos_demo` de
[src/flota/cli.py](../src/flota/cli.py).

### Ejercicios

1.1. En la consola, calculá cuántos km recorre un camión que va y vuelve de Albardón a Los Andes
(390 km cada tramo).

1.2. Con `print`, mostrá el nombre de la empresa y en la línea siguiente "Gestión de flota".

---

## 2. Variables y tipos de datos

**Vas a aprender:** a guardar datos con un nombre y los tipos básicos de Python.

Una **variable** es un nombre que apunta a un valor:

```python
>>> patente = "AB123CD"
>>> capacidad = 600
>>> activo = True
>>> anio = None
```

| Tipo | Ejemplo | Para qué |
|---|---|---|
| `int` (entero) | `600`, `-3` | Cantidades sin decimales |
| `float` (decimal binario) | `0.5`, `38.7` | Cálculos científicos (¡no dinero!) |
| `str` (texto) | `"AB123CD"` | Patentes, nombres |
| `bool` (lógico) | `True`, `False` | Sí / no: ¿está activo? |
| `None` | `None` | "No hay valor" (ej.: año desconocido) |
| `Decimal` | `Decimal("1450.50")` | **Dinero y litros** |

`type(x)` dice de qué tipo es algo: `type(600)` → `<class 'int'>`.

### Por qué el sistema usa `Decimal` y no `float`

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> from decimal import Decimal
>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')
```

Los `float` se guardan en binario y algunos números no se pueden representar exactos. Con litros
y pesos eso es inaceptable: por eso **todo importe y todo litro del sistema es `Decimal`**, y se
crea siempre desde texto (`Decimal("0.1")`, nunca `Decimal(0.1)`).

**En el sistema:** [catalogo/domain/entidades.py](../src/flota/catalogo/domain/entidades.py) declara
`capacidad_tanque_litros: Decimal` y `activo: bool = True`.

### Ejercicios

2.1. Guardá en variables los litros de una carga (`350.5`) y el precio por litro (`1450`) como
`Decimal`, y calculá el importe.

2.2. ¿De qué tipo es `None`? ¿Y `"600"`? ¿Es lo mismo `600` que `"600"`? Probá `600 + 1` y
`"600" + 1`: ¿qué error da el segundo y por qué?

---

## 3. Textos (strings)

**Vas a aprender:** a transformar textos con métodos y a armar mensajes con f-strings.

Un texto tiene **métodos**: funciones que se le aplican con un punto.

```python
>>> patente = "  ab 123-cd "
>>> patente.strip()          # saca espacios al principio y al final
'ab 123-cd'
>>> patente.upper()          # mayúsculas
'  AB 123-CD '
>>> "AB-123".replace("-", "")
'AB123'
```

Los métodos se pueden **encadenar**. Así funciona `normalizar_patente` del sistema
([catalogo/domain/entidades.py](../src/flota/catalogo/domain/entidades.py)):

```python
def normalizar_patente(patente: str) -> str:
    """'ab 123-cd' -> 'AB123CD'. Se usa tanto al guardar como al buscar."""
    return patente.strip().upper().replace(" ", "").replace("-", "")
```

**f-strings** (textos con `f` adelante) meten valores entre llaves:

```python
>>> litros = Decimal("42.567")
>>> f"Consumo: {litros:.1f} L/100km"      # :.1f = un decimal
'Consumo: 42.6 L/100km'
```

El sistema arma así los mensajes de las alertas
([alertas/application/casos_de_uso.py](../src/flota/alertas/application/casos_de_uso.py)).

### Ejercicios

3.1. Importá `normalizar_patente` (`from flota.catalogo.domain.entidades import normalizar_patente`)
y probala con `" ac-456 ef "`. Después escribí vos la misma transformación sin usar la función.

3.2. Con una f-string, armá el texto `"Ruta: Albardón → Mendoza (170 km)"` a partir de tres variables.

---

## 4. Listas y diccionarios

**Vas a aprender:** a guardar muchos datos juntos y a recorrerlos.

**Lista:** una secuencia ordenada, entre corchetes.

```python
>>> cargas = [Decimal("80"), Decimal("60"), Decimal("120")]
>>> len(cargas)                 # cuántos elementos
3
>>> cargas[0]                   # el primero (¡se cuenta desde 0!)
Decimal('80')
>>> sum(cargas, Decimal("0"))   # total
Decimal('260')
>>> cargas.append(Decimal("45"))  # agregar al final
```

**Diccionario:** pares `clave: valor`, entre llaves. Se busca por clave.

```python
>>> tanques = {"AB123CD": Decimal("600"), "AC456EF": Decimal("500")}
>>> tanques["AB123CD"]
Decimal('600')
>>> tanques.get("ZZ999ZZ")      # .get no da error si no existe: devuelve None
```

**Comprensión de lista:** crear una lista nueva filtrando o transformando otra, en una línea.

```python
>>> grandes = [c for c in cargas if c > 70]
```

Se lee: "cada `c` de `cargas`, si `c > 70`". El sistema la usa todo el tiempo; por ejemplo, para
quedarse con las cargas de un viaje
([combustible/domain/consumo.py](../src/flota/combustible/domain/consumo.py)):

```python
propias = [c for c in cargas if c.viaje_id == viaje.id and c.cuenta_para_consumo]
```

### Ejercicios

4.1. Con la lista `[Decimal("80"), Decimal("60"), Decimal("120")]`, calculá el total, la carga más
grande (`max`) y el promedio (total dividido `len`).

4.2. Creá un diccionario con tres patentes y su año. Mostrá el año de una patente y usá `.get` con
una patente que no exista.

4.3. Con una comprensión, armá la lista de las patentes de tu diccionario (pista: `.keys()`).

---

## 5. Decisiones y repeticiones

**Vas a aprender:** a ejecutar código según una condición (`if`) y a repetirlo (`for`).

```python
if litros > capacidad:
    print("Supera el tanque")
elif litros > capacidad * Decimal("0.9"):
    print("Casi lleno")
else:
    print("Normal")
```

- La **sangría** (4 espacios) indica qué está "adentro" del `if`. En Python no es estética: define
  el programa.
- Comparaciones: `==` (igual), `!=` (distinto), `>`, `<`, `>=`, `<=`.
- Lógicos: `and`, `or`, `not`.

**`for`** recorre una colección:

```python
for carga in cargas:
    print(carga)
```

**En el sistema:** la regla RF-18 (la carga supera el tanque, con un 5 % de tolerancia), en
[combustible/domain/entidades.py](../src/flota/combustible/domain/entidades.py):

```python
def supera_tanque(self, capacidad: Decimal, tolerancia_pct: Decimal) -> bool:
    return self.litros > capacidad * (1 + tolerancia_pct / 100)
```

Una comparación da `True` o `False`: por eso puede devolverse directamente.

### Ejercicios

5.1. Escribí un `for` que recorra `[Decimal("650"), Decimal("620"), Decimal("300")]` y, para un tanque
de 600 L con 5 % de tolerancia, imprima "supera" o "ok" para cada carga.

5.2. Contá cuántas cargas superan 100 litros en una lista, usando un `for` y una variable contador.
Después hacelo en una línea con `sum(1 for c in cargas if c > 100)`.

---

## 6. Funciones

**Vas a aprender:** a empaquetar código reutilizable con `def`.

```python
def l100km(litros: Decimal, km: Decimal | None) -> Decimal | None:
    if not km or not litros:
        return None
    return (litros / km * 100).quantize(DOS_DECIMALES)
```

Esta es la fórmula del consumo del sistema
([combustible/domain/consumo.py](../src/flota/combustible/domain/consumo.py)):

- `def nombre(parámetros):` define la función; `return` devuelve el resultado.
- `litros: Decimal` y `-> Decimal | None` son **anotaciones de tipo**: documentan qué recibe y qué
  devuelve. `Decimal | None` significa "un Decimal o nada" (si no hay km, no hay consumo).
- `.quantize(Decimal("0.01"))` redondea a dos decimales.
- `if not km` es verdadero si `km` es `None` o `0`: evita dividir por cero.

**Parámetros con valor por defecto:**

```python
def calcular_consumo(viaje, camion, cargas, umbral_desvio_pct=Decimal("15"), ruta=None): ...
```

Si no se pasa `umbral_desvio_pct`, vale 15. Al llamar se puede dar el nombre del parámetro:
`calcular_consumo(viaje, camion, cargas, ruta=mi_ruta)`.

### Probalo

```python
>>> from decimal import Decimal
>>> from flota.combustible.domain.consumo import l100km, desvio_pct
>>> l100km(Decimal("84"), Decimal("200"))
Decimal('42.00')
>>> desvio_pct(Decimal("50"), Decimal("40"))
Decimal('25.0')
```

### Ejercicios

6.1. Escribí `costo_por_km(costo, km)` que devuelva el costo por km con dos decimales, o `None` si
no hay km. Probala con 145000 pesos y 400 km.

6.2. ¿Qué devuelve `l100km(Decimal("84"), None)`? ¿Por qué es mejor eso que un error?

---

# Parte 2 — Programar con objetos

## 7. Clases y dataclasses

**Vas a aprender:** a crear tus propios tipos de datos, con sus datos y sus reglas.

Una **clase** es un molde; un **objeto** es algo hecho con ese molde. `Camion` es una clase;
el Scania AB123CD es un objeto.

```python
@dataclass(kw_only=True)
class Camion:
    patente: str
    marca: str
    modelo: str
    capacidad_tanque_litros: Decimal
    consumo_referencia_l100km: Decimal
    km_actual: Decimal | None = None
    activo: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.patente = normalizar_patente(requerido(self.patente, "patente"))
        positivo(self.capacidad_tanque_litros, "capacidad_tanque_litros")

    def registrar_km(self, km: Decimal) -> None:
        """El odómetro nunca retrocede."""
        if self.km_actual is None or km > self.km_actual:
            self.km_actual = km
```

([catalogo/domain/entidades.py](../src/flota/catalogo/domain/entidades.py))

- `@dataclass` es un **decorador**: le agrega a la clase el código para crear objetos con esos
  campos, compararlos y mostrarlos.
- `kw_only=True` obliga a crear el objeto nombrando cada campo (más claro y sin errores de orden).
- `__post_init__` se ejecuta al crear el objeto: ahí van las **validaciones**. Un camión con
  capacidad 0 no se puede crear.
- Un **método** es una función que pertenece a la clase. `self` es "este objeto".
- `field(default_factory=uuid4)` genera un id nuevo para cada camión.

### Probalo

```python
>>> from decimal import Decimal
>>> from flota.catalogo.domain.entidades import Camion
>>> camion = Camion(patente="ab 123-cd", marca="Scania", modelo="R450",
...                 capacidad_tanque_litros=Decimal("600"),
...                 consumo_referencia_l100km=Decimal("40"))
>>> camion.patente
'AB123CD'
>>> camion.registrar_km(Decimal("125000"))
>>> camion.registrar_km(Decimal("124000"))   # una lectura vieja: se ignora
>>> camion.km_actual
Decimal('125000')
```

### Ejercicios

7.1. Intentá crear un camión con `capacidad_tanque_litros=Decimal("0")`. ¿Qué error da?

7.2. Escribí tu propia dataclass `Estacion` con `nombre: str` y `pais: str = "AR"`, y un método
`es_chilena()` que devuelva `True` si el país es `"CL"`.

---

## 8. Enumeraciones y propiedades

**Vas a aprender:** a definir listas cerradas de valores (`Enum`) y datos calculados (`@property`).

```python
class EstadoCarga(StrEnum):
    CARGADO = "cargado"
    VACIO = "vacio"
```

Un **enum** es un conjunto fijo de opciones. Si escribís `EstadoCarga.VACIOO`, Python avisa el
error; con textos sueltos (`"vacioo"`) el error pasaría inadvertido. Al ser `StrEnum`, también
se comporta como texto: `EstadoCarga.VACIO == "vacio"` es `True`.

**`@property`** convierte un método en un dato que se lee sin paréntesis:

```python
@dataclass(kw_only=True)
class Ruta:
    origen: str
    destino: str
    ...
    @property
    def nombre(self) -> str:
        return f"{self.origen} → {self.destino}"
```

([viajes/domain/entidades.py](../src/flota/viajes/domain/entidades.py)) `ruta.nombre` se calcula cada
vez a partir de origen y destino: nunca queda desactualizado.

### Probalo

```python
>>> from decimal import Decimal
>>> from flota.viajes.domain.entidades import Ruta, Pais, EstadoCarga
>>> ruta = Ruta(origen="Albardón", destino="Los Andes", pais=Pais.CL,
...             ref_l100_cargado=Decimal("48"))
>>> ruta.nombre
'Albardón → Los Andes'
>>> ruta.referencia_configurada(EstadoCarga.CARGADO)
Decimal('48')
>>> list(Pais)
[<Pais.AR: 'AR'>, <Pais.CL: 'CL'>]
```

### Ejercicios

8.1. ¿Qué devuelve `ruta.referencia_configurada(EstadoCarga.VACIO)` en el ejemplo? ¿Por qué?

8.2. Agregá a tu `Estacion` del ejercicio 7.2 una propiedad `descripcion` que devuelva
`"YPF Ruta 40 (AR)"`.

---

## 9. Errores y excepciones

**Vas a aprender:** a avisar que algo está mal (`raise`) y a manejar errores (`try/except`).

Cuando una regla del negocio no se cumple, el sistema **lanza una excepción**:

```python
def positivo(valor, campo):
    if valor is None or valor <= 0:
        raise DatosInvalidos(f"El campo '{campo}' debe ser mayor a cero")
    return valor
```

([shared/domain/validaciones.py](../src/flota/shared/domain/validaciones.py))

`raise` corta la ejecución y "sube" el error hasta que alguien lo atrapa con `try/except`:

```python
try:
    camion = Camion(..., capacidad_tanque_litros=Decimal("0"), ...)
except DatosInvalidos as error:
    print("No se pudo:", error)
```

**Errores propios con jerarquía** ([shared/domain/errores.py](../src/flota/shared/domain/errores.py)):

```python
class ErrorDominio(Exception): ...
class DatosInvalidos(ErrorDominio): ...       # dato mal formado        -> HTTP 422
class NoEncontrado(ErrorDominio): ...         # no existe               -> HTTP 404
class Duplicado(ErrorDominio): ...            # ya existe               -> HTTP 409
class ReglaNegocioViolada(ErrorDominio): ...  # no está permitido       -> HTTP 400
```

`class DatosInvalidos(ErrorDominio)` significa que `DatosInvalidos` **hereda** de `ErrorDominio`: es
un caso particular. Por eso `except ErrorDominio` atrapa todos. La API traduce cada uno a su código
HTTP en un solo lugar ([main.py](../src/flota/main.py)).

### Ejercicios

9.1. Escribí una función `dividir(a, b)` que lance `ValueError("No se puede dividir por cero")` si
`b` es 0. Llamala dentro de un `try/except` que muestre el mensaje.

9.2. Intentá finalizar dos veces el mismo viaje (lección 11). ¿Qué excepción da?

---

## 10. Objetos de valor y métodos especiales

**Vas a aprender:** a que tus objetos funcionen con `+`, `*`, `<` y a crear objetos inmutables.

`Dinero` ([shared/domain/dinero.py](../src/flota/shared/domain/dinero.py)) junta un monto y su moneda:

```python
@dataclass(frozen=True)
class Dinero:
    monto: Decimal
    moneda: Moneda = Moneda.ARS

    def __add__(self, otro: Dinero) -> Dinero:
        self._misma_moneda(otro)       # pesos argentinos + chilenos -> error
        return Dinero(self.monto + otro.monto, self.moneda)
```

- `frozen=True`: el objeto es **inmutable** (no se puede cambiar después de crearlo). Sumar
  devuelve un `Dinero` nuevo.
- Los métodos con doble guion bajo son **especiales**: `a + b` llama a `a.__add__(b)`, `a * 2` llama
  a `__mul__`, `a < b` llama a `__lt__`.
- Es un **objeto de valor**: no tiene id; dos `Dinero(100, ARS)` son lo mismo.

### Probalo

```python
>>> from decimal import Decimal
>>> from flota.shared.domain.dinero import Dinero, Moneda
>>> a = Dinero(Decimal("1000"), Moneda.CLP)
>>> a + Dinero(Decimal("500"), Moneda.CLP)
Dinero(monto=Decimal('1500'), moneda=<Moneda.CLP: 'CLP'>)
>>> a + Dinero(Decimal("1"), Moneda.ARS)
... ReglaNegocioViolada: No se pueden operar CLP y ARS sin convertir antes
```

### Ejercicios

10.1. Probá `a.monto = Decimal("5")`. ¿Qué pasa y por qué?

10.2. Calculá `a * 3` y `a < Dinero(Decimal("2000"), Moneda.CLP)`.

---

## 11. Objetos que contienen objetos

**Vas a aprender:** a combinar objetos (un viaje con sus tramos) y a usar `@classmethod`.

Un `Viaje` tiene una **lista de `TramoViaje`** (cargado / vacío). Para crear un viaje nuevo con su
primer tramo se usa un **método de clase** ([viajes/domain/entidades.py](../src/flota/viajes/domain/entidades.py)):

```python
@classmethod
def iniciar(cls, *, camion_id, chofer_id, ruta_id, fecha_salida, km_salida, ...) -> Viaje:
    primer_tramo = TramoViaje(estado_carga=estado_carga, fecha_inicio=fecha_salida, km_inicio=km_salida)
    return cls(..., tramos=[primer_tramo])
```

`cls` es la clase misma: `Viaje.iniciar(...)` es un "constructor con nombre". Los tramos sólo se
modifican a través del viaje (`registrar_descarga`, `finalizar`): el viaje controla sus reglas.

### Probalo

```python
>>> from datetime import datetime, timedelta
>>> from decimal import Decimal
>>> from uuid import uuid4
>>> from flota.viajes.domain.entidades import Viaje
>>> salida = datetime(2026, 10, 1, 8)
>>> viaje = Viaje.iniciar(camion_id=uuid4(), chofer_id=uuid4(), ruta_id=uuid4(),
...                       fecha_salida=salida, km_salida=Decimal("1000"),
...                       producto_id=uuid4(), cantidad=Decimal("28"))
>>> viaje.registrar_descarga(salida + timedelta(hours=5), Decimal("1200"))
>>> viaje.finalizar(salida + timedelta(hours=10), Decimal("1400"))
>>> [t.estado_carga for t in viaje.tramos]
[<EstadoCarga.CARGADO: 'cargado'>, <EstadoCarga.VACIO: 'vacio'>]
>>> viaje.km_recorridos
Decimal('400')
```

`datetime` representa fecha y hora; `timedelta(hours=5)` es "5 horas", y se pueden sumar.

### Ejercicios

11.1. Intentá registrar la descarga con un odómetro menor al de salida. ¿Qué error da?

11.2. Mostrá los km de cada tramo con una comprensión: `[t.km_recorridos for t in viaje.tramos]`.

---

# Parte 3 — Organizar un programa grande

## 12. Módulos, paquetes e imports

**Vas a aprender:** cómo se reparte un programa en muchos archivos.

- Un **módulo** es un archivo `.py`. Un **paquete** es una carpeta con un `__init__.py`.
- `from flota.viajes.domain.entidades import Viaje` significa: en el paquete `flota`, subpaquete
  `viajes`, subpaquete `domain`, módulo `entidades`, traé `Viaje`.

El sistema está organizado **por módulo del negocio** y, dentro, **por capa**:

```
src/flota/viajes/
├── domain/           reglas puras: Ruta, Viaje, TramoViaje
├── application/      casos de uso: IniciarViaje, FinalizarViaje…
├── infrastructure/   base de datos
└── presentation/     API y páginas web
```

**Regla de dependencias:** `domain` no importa nada de las otras capas. Así las reglas del negocio
se pueden probar sin base de datos ni servidor web. Detalle en la guía técnica
([guia-tecnica.md](guia-tecnica.md), sección 5).

`if __name__ == "__main__":` (al final de algunos archivos) significa "esto corre sólo si ejecuto
este archivo directamente, no si lo importo desde otro".

### Ejercicios

12.1. Abrí [src/flota/combustible/domain/consumo.py](../src/flota/combustible/domain/consumo.py) y
anotá de qué módulos importa. ¿Alguno es de `infrastructure` o `presentation`?

12.2. Creá un archivo `prueba.py` en la carpeta del proyecto que importe `normalizar_patente` e
imprima una patente normalizada. Ejecutalo con `uv run python prueba.py`. (Después borralo.)

---

## 13. Tipos, interfaces y casos de uso

**Vas a aprender:** qué es una interfaz y cómo el sistema separa "qué necesito" de "cómo se hace".

**Interfaz con `ABC`:** un contrato de métodos que otras clases deben implementar
([catalogo/domain/repositorios.py](../src/flota/catalogo/domain/repositorios.py)):

```python
class RepositorioCamiones(Repositorio[Camion]):
    @abstractmethod
    def obtener_por_patente(self, patente: str) -> Camion | None: ...
```

Hay dos implementaciones: una con la base de datos real (SQL) y otra **en memoria** para los tests
([tests/fakes.py](../tests/fakes.py)). El **caso de uso** no sabe cuál recibe:

```python
class RegistrarCamion:
    def __init__(self, uow: UoWCatalogo) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosCamion) -> Camion:
        camion = Camion(**asdict(datos))
        with self._uow as uow:
            if uow.camiones.obtener_por_patente(camion.patente):
                raise Duplicado(f"Ya existe un camión con patente {camion.patente}")
            uow.camiones.guardar(camion)
            uow.commit()
        return camion
```

Esto se llama **inyección de dependencias**: la clase recibe lo que necesita (`uow`) en lugar de
crearlo. Por eso se puede probar con la versión en memoria.

`**asdict(datos)` convierte la dataclass `datos` en diccionario y lo "desparrama" como argumentos
con nombre: `Camion(patente=..., marca=..., ...)`.

### Probalo

```python
>>> from decimal import Decimal
>>> from flota.catalogo.application.casos_de_uso import DatosCamion, RegistrarCamion
>>> from tests.fakes import UnidadDeTrabajoFake
>>> uow = UnidadDeTrabajoFake()
>>> RegistrarCamion(uow).ejecutar(DatosCamion("AB123CD", "Scania", "R450",
...                                           Decimal("600"), Decimal("40")))
>>> RegistrarCamion(uow).ejecutar(DatosCamion("ab-123-cd", "Iveco", "S",
...                                           Decimal("500"), Decimal("35")))
... Duplicado: Ya existe un camión con patente AB123CD
```

### Ejercicios

13.1. Después del ejemplo, ¿cuánto vale `uow.commits`? ¿Por qué no es 2?

13.2. Registrá un chofer con `RegistrarChofer` y `DatosChofer("Juan Pérez", "30.123.456")` en el
mismo `uow`. ¿Cómo quedó guardado el DNI?

---

## 14. `with`, funciones como valores y eventos

**Vas a aprender:** los bloques `with`, a pasar funciones como datos y el patrón de eventos.

**`with`** garantiza que algo se cierre bien aunque haya un error. En el sistema, cada caso de uso
abre una **transacción**: si no se llama a `commit()`, al salir del `with` se descarta todo.

```python
with self._uow as uow:       # abre la transacción
    uow.camiones.guardar(camion)
    uow.commit()             # confirma
# al salir: se cierra; si hubo error antes del commit, nada se guardó
```

**Funciones como valores.** En Python una función es un dato: se puede guardar en una variable o
pasar a otra función. `lambda` crea una función corta sin nombre:

```python
>>> doble = lambda x: x * 2
>>> doble(21)
42
```

**Eventos.** Cuando un viaje se finaliza, el módulo de viajes **publica** un evento
`ViajeFinalizado` y el módulo de alertas, que está **suscripto**, evalúa el consumo. Viajes no
conoce a alertas ([shared/application/eventos.py](../src/flota/shared/application/eventos.py)):

```python
>>> from dataclasses import dataclass
>>> from flota.shared.application.eventos import BusEventos
>>> from flota.shared.domain.eventos import Evento
>>> @dataclass(frozen=True)
... class Saludo(Evento):
...     nombre: str
>>> bus = BusEventos()
>>> bus.suscribir(Saludo, lambda evento: print("Hola", evento.nombre))
>>> bus.publicar(Saludo("Silvana"))
Hola Silvana
```

### Ejercicios

14.1. Suscribí al mismo bus una segunda función que imprima `"Llegó un saludo"`. Publicá otro
`Saludo`: ¿se ejecutan las dos?

14.2. ¿Qué pasa si un manejador lanza un error? Probá suscribir
`lambda e: 1 / 0` y publicar. (Pista: mirá [eventos.py](../src/flota/shared/application/eventos.py).)

---

## 15. Generadores

**Vas a aprender:** a producir resultados de a uno con `yield`.

Una función con `yield` no devuelve todo junto: **entrega un valor por vez**, cuando se le pide.
El importador de archivos lo usa para leer planillas grandes fila por fila
([combustible/infrastructure/importacion/mapeo.py](../src/flota/combustible/infrastructure/importacion/mapeo.py)):

```python
for numero, valores in filas:
    try:
        ...
        yield FilaCarga(...)            # una fila buena
    except ValueError as error:
        yield ErrorLectura(numero, str(error))   # o un error, y sigue con la próxima
```

Ventajas: usa poca memoria, y una fila con error no frena el resto del archivo.

```python
>>> def numeros_pares(hasta):
...     for n in range(hasta):
...         if n % 2 == 0:
...             yield n
>>> list(numeros_pares(10))
[0, 2, 4, 6, 8]
```

### Ejercicios

15.1. Escribí un generador `tramos_de(km_total, largo)` que entregue los km de inicio de cada
tramo: `list(tramos_de(1000, 300))` → `[0, 300, 600, 900]`.

---

# Parte 4 — Las librerías del sistema

## 16. Pydantic y FastAPI

**Vas a aprender:** cómo una petición web llega a un caso de uso.

**Pydantic** valida datos que vienen de afuera (JSON) usando los tipos
([catalogo/presentation/esquemas.py](../src/flota/catalogo/presentation/esquemas.py)):

```python
class CamionCrear(BaseModel):
    patente: str = Field(min_length=6, max_length=15)
    capacidad_tanque_litros: Decimal = Field(gt=0)
```

Si llega `"capacidad_tanque_litros": -5`, Pydantic responde automáticamente con un error 422.

**FastAPI** conecta una URL con una función ([catalogo/presentation/api.py](../src/flota/catalogo/presentation/api.py)):

```python
@router.post("/camiones", response_model=CamionLeer, status_code=201)
def crear_camion(datos: CamionCrear, uow: UoW):
    camion = RegistrarCamion(uow).ejecutar(DatosCamion(**datos.model_dump()))
    return CamionLeer.model_validate(camion)
```

- `@router.post("/camiones")`: este decorador dice "cuando llegue un POST a /camiones, ejecutá esta función".
- `datos: CamionCrear`: FastAPI lee el JSON y lo valida con Pydantic.
- `uow: UoW`: FastAPI **inyecta** la unidad de trabajo (inyección de dependencias).

### Ejercicio

16.1. Con el servidor corriendo, abrí `http://127.0.0.1:8000/docs`, buscá `POST /api/v1/camiones`,
apretá *Try it out* y mandá una capacidad negativa. Mirá el error 422. Después mandá datos válidos.
(La API pide iniciar sesión: entrá primero al panel con tu usuario en el mismo navegador.)

---

## 17. SQLAlchemy y la base de datos

**Vas a aprender:** cómo los objetos se guardan en tablas.

Un **modelo** describe una tabla ([catalogo/infrastructure/modelos.py](../src/flota/catalogo/infrastructure/modelos.py)):

```python
class CamionModel(ConAuditoria, Base):
    __tablename__ = "camiones"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    patente: Mapped[str] = mapped_column(String(15), unique=True, index=True)
```

El **repositorio** traduce entre la entidad (`Camion`) y el modelo (`CamionModel`) y hace las
consultas ([catalogo/infrastructure/repositorios.py](../src/flota/catalogo/infrastructure/repositorios.py)):

```python
def obtener_por_patente(self, patente: str) -> Camion | None:
    return self._uno(select(CamionModel).where(CamionModel.patente == patente))
```

`select(...).where(...)` es SQL escrito en Python: equivale a
`SELECT * FROM camiones WHERE patente = 'AB123CD'`.

**Migraciones (Alembic):** cada cambio en las tablas es un archivo en
[migrations/versions/](../migrations/versions/), y `uv run alembic upgrade head` los aplica.

### Ejercicio

17.1. Abrí la migración de la Sesión 4 (`..._rutas_y_tramos_de_viaje.py`) y buscá los cuatro pasos de
`upgrade()`. ¿Por qué `ruta_id` se crea primero como opcional?

---

## 18. Tests con pytest

**Vas a aprender:** a comprobar automáticamente que el código hace lo que debe.

Un test es una función que empieza con `test_` y usa `assert` (afirmar):

```python
def test_camion_normaliza_patente():
    assert nuevo_camion().patente == "AB123CD"
```

([tests/unit/test_catalogo.py](../tests/unit/test_catalogo.py)) Si la afirmación es falsa, el test
falla y pytest muestra qué esperaba y qué obtuvo. Para probar que algo **debe** dar error:

```python
def test_camion_rechaza_capacidad_no_positiva():
    with pytest.raises(DatosInvalidos):
        nuevo_camion(capacidad_tanque_litros=Decimal("0"))
```

Correr los tests:

```powershell
uv run pytest                          # todos (más de 120)
uv run pytest tests/unit/test_viajes.py -v   # un archivo, con detalle
uv run pytest -k patente               # los que tienen "patente" en el nombre
```

### Ejercicios

18.1. Corré `uv run pytest -k patente -v`. ¿Cuántos tests encontró?

18.2. **Romper a propósito:** en [catalogo/domain/entidades.py](../src/flota/catalogo/domain/entidades.py),
sacá `.upper()` de `normalizar_patente`, corré los tests y leé el error. **Después volvelo a poner**
y verificá que todo pase de nuevo.

---

# Parte 5 — Práctica final

## 19. Proyecto guiado: agregar una funcionalidad

Vas a agregar al sistema la **duración de un viaje en horas**, siguiendo el mismo camino que en
cada sesión de desarrollo: dominio → test → presentación. Trabajá en una rama de git para poder
descartar todo si algo sale mal:

```powershell
git switch -c practica-duracion
```

**Paso 1 — Dominio.** En [viajes/domain/entidades.py](../src/flota/viajes/domain/entidades.py), dentro
de la clase `Viaje`, junto a `km_recorridos`, agregá:

```python
@property
def duracion_horas(self) -> Decimal | None:
    """Horas entre la salida y la llegada (None si el viaje sigue en curso)."""
    if self.fecha_llegada is None:
        return None
    segundos = (self.fecha_llegada - self.fecha_salida).total_seconds()
    return (Decimal(str(segundos)) / 3600).quantize(Decimal("0.1"))
```

**Paso 2 — Test.** En [tests/unit/test_viajes.py](../tests/unit/test_viajes.py) agregá:

```python
def test_duracion_del_viaje():
    viaje = nuevo_viaje()
    assert viaje.duracion_horas is None
    viaje.finalizar(SALIDA + timedelta(hours=10, minutes=30), Decimal("1400"))
    assert viaje.duracion_horas == Decimal("10.5")
```

Corré `uv run pytest tests/unit/test_viajes.py -v`.

**Paso 3 — API.** En [viajes/presentation/esquemas.py](../src/flota/viajes/presentation/esquemas.py),
en `ViajeLeer`, agregá `duracion_horas: Numero | None`. Levantá el servidor y mirá `GET /api/v1/viajes`
en `/docs`: aparece el campo nuevo.

**Paso 4 — Calidad.** `uv run ruff check .` y `uv run pytest`: todo en verde.

**Para terminar:** si querés conservarlo, `git add -A` y `git commit -m "Duración del viaje"`; si
no, `git switch main` y `git branch -D practica-duracion`.

Si llegaste hasta acá, ya hiciste el recorrido completo de un desarrollador del sistema.

---

## Soluciones de los ejercicios

**1.1** `390 * 2` → `780`. **1.2** `print("Transportes Hidalgo")` y `print("Gestión de flota")`.

**2.1**
```python
from decimal import Decimal
litros = Decimal("350.5")
precio = Decimal("1450")
litros * precio          # Decimal('508225.0')
```
**2.2** `type(None)` → `NoneType`; `type("600")` → `str`. No es lo mismo: `600` es un número y
`"600"` un texto. `"600" + 1` da `TypeError`: no se puede sumar texto con número (habría que
convertir: `int("600") + 1`).

**3.1** `" ac-456 ef ".strip().upper().replace(" ", "").replace("-", "")` → `'AC456EF'`.
**3.2**
```python
origen, destino, km = "Albardón", "Mendoza", 170
f"Ruta: {origen} → {destino} ({km} km)"
```

**4.1**
```python
cargas = [Decimal("80"), Decimal("60"), Decimal("120")]
total = sum(cargas, Decimal("0"))   # 260
max(cargas)                         # 120
total / len(cargas)                 # 86.666…
```
**4.2** `anios = {"AB123CD": 2019, "AC456EF": 2021, "AD789GH": 2018}`; `anios["AB123CD"]`;
`anios.get("ZZ")` → `None`. **4.3** `[p for p in anios.keys()]` (o simplemente `list(anios)`).

**5.1**
```python
for litros in [Decimal("650"), Decimal("620"), Decimal("300")]:
    if litros > Decimal("600") * Decimal("1.05"):
        print(litros, "supera")
    else:
        print(litros, "ok")
```
(650 supera; 620 y 300 ok: el límite con tolerancia es 630.)
**5.2**
```python
contador = 0
for c in cargas:
    if c > 100:
        contador += 1
```

**6.1**
```python
def costo_por_km(costo, km):
    if not km:
        return None
    return (costo / km).quantize(Decimal("0.01"))

costo_por_km(Decimal("145000"), Decimal("400"))   # Decimal('362.50')
```
**6.2** Devuelve `None`. Un viaje en curso todavía no tiene km: no es un error, es un dato que
falta. Las pantallas muestran "—".

**7.1** `DatosInvalidos: El campo 'capacidad_tanque_litros' debe ser mayor a cero`.
**7.2**
```python
from dataclasses import dataclass

@dataclass
class Estacion:
    nombre: str
    pais: str = "AR"

    def es_chilena(self) -> bool:
        return self.pais == "CL"
```

**8.1** `None`: la ruta no tiene referencia configurada para el tramo vacío; el sistema usa
entonces el histórico de la ruta o la referencia del camión.
**8.2**
```python
    @property
    def descripcion(self) -> str:
        return f"{self.nombre} ({self.pais})"
```

**9.1**
```python
def dividir(a, b):
    if b == 0:
        raise ValueError("No se puede dividir por cero")
    return a / b

try:
    dividir(10, 0)
except ValueError as error:
    print(error)
```
**9.2** `ReglaNegocioViolada: El viaje ya está finalizado`.

**10.1** `FrozenInstanceError`: el objeto es inmutable (`frozen=True`).
**10.2** `a * 3` → `Dinero(3000, CLP)`; la comparación da `True`.

**11.1** `DatosInvalidos: El odómetro (900 km) debe ser mayor al del inicio del tramo (1000 km)`.
**11.2** `[Decimal('200'), Decimal('200')]`.

**12.1** Importa de `flota.catalogo.domain`, `flota.combustible.domain`, `flota.shared.domain` y
`flota.viajes.domain`: todo dominio. Ninguno de infraestructura ni presentación: por eso se puede
probar sin base de datos.

**13.1** `1`: el segundo registro lanzó `Duplicado` antes del `commit`.
**13.2** `"30123456"`: el chofer guarda sólo los dígitos del DNI (`__post_init__`).

**14.1** Sí, se ejecutan las dos, en el orden en que se suscribieron.
**14.2** El bus registra el error en el log y sigue: la operación que publicó el evento no se
deshace. Así, por ejemplo, un viaje se finaliza aunque falle el cálculo de alertas.

**15.1**
```python
def tramos_de(km_total, largo):
    km = 0
    while km < km_total:
        yield km
        km += largo
```

**16.1** Con capacidad negativa: 422 y el detalle `Input should be greater than 0`. Con datos
válidos: 201 y el camión creado, con su `id`.

**17.1** Porque ya había viajes guardados: si la columna fuera obligatoria desde el principio, esas
filas no tendrían valor y la base rechazaría el cambio. Primero se agrega opcional, se completan
los datos y después se vuelve obligatoria.

**18.1** Al escribir este curso, 2 tests: `test_camion_normaliza_patente` y
`test_no_permite_patente_duplicada` (el número puede crecer con el sistema).
**18.2** Fallan los tests de patentes: esperaban `'AB123CD'` y obtienen `'ab123cd'`.

---

## Hoja de referencia rápida

| Quiero… | Python |
|---|---|
| Guardar un dato | `patente = "AB123CD"` |
| Dinero o litros exactos | `Decimal("1450.50")` |
| Un texto con valores | `f"{litros:.1f} L"` |
| Una lista | `cargas = [1, 2, 3]`; `cargas.append(4)`; `cargas[0]` |
| Un diccionario | `d = {"clave": valor}`; `d["clave"]`; `d.get("x")` |
| Filtrar una lista | `[c for c in cargas if c > 100]` |
| Decidir | `if x > 0: … elif …: … else: …` |
| Repetir | `for c in cargas: …` |
| Una función | `def nombre(a, b=1) -> tipo: return …` |
| Un tipo propio | `@dataclass class Camion: patente: str` |
| Un dato calculado | `@property def nombre(self): …` |
| Opciones fijas | `class Estado(StrEnum): A = "a"` |
| Avisar un error | `raise DatosInvalidos("mensaje")` |
| Atrapar un error | `try: … except DatosInvalidos as e: …` |
| Abrir y cerrar seguro | `with uow: …` |
| Entregar de a uno | `yield valor` |
| Probar | `def test_algo(): assert x == y` |

---

## Cómo seguir aprendiendo

1. Leé la [guía técnica](guia-tecnica.md): profundiza cada concepto con más ejemplos del sistema.
2. Leé las notas de cada sesión en `docs/sesiones/`: cuentan **por qué** se tomó cada decisión.
3. Elegí un caso de uso (por ejemplo `CambiarEstadoCarga`) y seguilo por todas las capas: página
   web → ruta → caso de uso → entidad → repositorio → tabla.
4. Repetí el proyecto guiado con otra idea chica: costo por tonelada transportada, cantidad de
   viajes por chofer en el mes, etc.
5. Documentación oficial en español: el tutorial de Python (docs.python.org/es/3/tutorial) y la de
   FastAPI (fastapi.tiangolo.com/es).

Este curso se actualiza cuando el sistema cambia.
