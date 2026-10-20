# 07 Plataforma en la nube

*Prompts de Fortino Romero Mantilla · IA usada: Claude (Anthropic)*

## Una propuesta basada en las bases
**Lo que pedimos:** "Propón la interfaz a partir de las bases del reto: nuestra fuente de verdad son las bases, y si algo no coincide con lo que piden, no lo agregues. Toma ideas de las propuestas de Andrea y Jared, pero no copies su texto ni su código."

**Qué salió:** un prototipo donde cada sección responde a un punto de las bases (consultar, ejecutar, explicar, inclusión financiera, preguntas guía). Lo revisamos y pedimos cambios de diseño.

## Primero el back, luego el front
**Lo que pedimos:** "Decide si conviene empezar por el back o por el diseño. Usamos Terraform y AWS: quiero el modelo y los datos en la nube antes de pulir la página, en el mismo repositorio que el modelo."

**Qué salió:** una función en la nube que reentrena el modelo con las 138 parcelas y produce un CSV idéntico al de la entrega, y la infraestructura escrita como código. La desplegamos y probamos nosotros.

## Correcciones de diseño
**Lo que pedimos:** "El contenido me gustó, pero la tipografía no me convence. Basa la letra y la organización en el sitio de AWS UG Puebla, con un poco más de espacio y negritas, sin exagerar. Reorganiza la portada con los logos según mi boceto. Quita la barra de pestañas y el marco negro del indicador de etapa. La unión de capas pasa muy rápido: hazla más lenta y que se deshaga al regresar. Evita los recuadros redondeados que se ven genéricos."

**Qué salió:** el sitio definitivo con un indicador de sección minimalista, la animación ligada al scroll y una versión propia para teléfono. Revisamos cada versión en el celular y pedimos ajustes puntuales (el círculo del minimapa, la gráfica cortada).

## Dominio propio y documentación del diseño
**Lo que pedimos:** "Ponle el subdominio agrocebada.foor.dev. Luego documenta las decisiones de diseño para que cualquiera del equipo pueda seguir el mismo estilo."

**Qué salió:** el certificado y el subdominio configurados (los registros DNS los creamos nosotros) y una guía de diseño para el equipo.
