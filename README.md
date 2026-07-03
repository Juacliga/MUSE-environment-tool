# MUSE Environment Tool 🛰️

Herramienta computacional híbrida para la simulación y análisis de efectos del entorno espacial en misiones en Órbita Terrestre Baja (LEO). 

Este software ha sido desarrollado como parte del Trabajo de Fin de Grado (TFG) en Ingeniería Aeroespacial por la Universitat Politècnica de València (UPV).

**Autor:** Juan Climent García

---

## 📋 Descripción General

MUSE Environment Tool permite evaluar de forma integral la supervivencia y el rendimiento de plataformas espaciales frente a las severidades del entorno LEO. La arquitectura del software se divide en una Interfaz Gráfica de Usuario (*Front-end*) desarrollada en Python y un motor de cálculo numérico (*Back-end*) operado mediante MATLAB.

### Módulos de Simulación Principales:
* **Decaimiento Orbital (Aerodinámica):** Propagación de trayectoria mediante ecuaciones de perturbación de Gauss y el modelo atmosférico NRLMSISE-00.
* **Impactos Hiperveloces (MMOD):** Evaluación de probabilidad de penetración y dimensionamiento de escudos Whipple utilizando las ecuaciones empíricas de Cour-Palais.
* **Radiación y Efectos Eléctricos:** Procesamiento de datos de SPENVIS para evaluar la Dosis Ionizante Total (TID) y el Daño por Desplazamiento (DD) en paneles fotovoltaicos.
* **Degradación de Materiales:** Estimación de pérdida de masa por erosión de Oxígeno Atómico (ATOX) en polímeros de uso espacial (Kapton, Teflón).
* **Balance Térmico:** Cálculo de potencias térmicas incidentes (Radiación solar, Albedo, Infrarrojo terrestre y disipación al espacio profundo).

---

## ⚙️ Requisitos del Sistema

Para garantizar la correcta compilación y ejecución de la herramienta, el equipo debe cumplir con las siguientes dependencias:

### Back-end (MATLAB)
* MATLAB (Versión compatible con la API de Python).
* **Aerospace Toolbox** (Requisito obligatorio para la resolución nativa del modelo atmosférico).

### Front-end (Python)
* Intérprete de Python 64-bit (Recomendado: 3.12 o 3.13).
* Librerías estrictas del entorno virtual:
  ```bash
  pip install customtkinter matplotlib numpy requests matlabengine
