# Diagnóstico de los datos de origen

Relevamiento hecho **antes** de programar el pipeline (01/11/2026). Sustenta las decisiones de
[DECISIONES.md](DECISIONES.md).

Fuentes: los tres archivos de planilla entregados por la cátedra (reporte de Ventas, reporte de
Compras y lista del proveedor).

## ERP1 — Reporte de Ventas (`erp1_ventas.xlsx`)

| Aspecto | Resultado |
|---|---|
| Filas | 2.184 |
| Columnas | Categoría, Código, Producto/Nombre, Precio |
| Nulos | 0 en todas las columnas |
| Códigos duplicados | 0 |
| Formato de precio | Numérico, sin vacíos. El pipeline también acepta el formato argentino como texto (`$ 102.733,76`) por si una exportación futura lo trae así |
| Precios en 0 | **9**: FIS 020/022/032/039/040/096/204001, 3240113 y 30091. Los 9 están además entre los artículos no cruzados |
| Largo de nombre | mín 19, mediana 55, máx 449; 286 superan 90 caracteres |

## ERP2 — Reporte de Compras (`erp2_compras.xlsx`)

| Aspecto | Resultado |
|---|---|
| Filas | 2.184 |
| Columnas | Marca, Categoría, Código, Nombre, Costo, Codigo Proveedor |
| Coincidencia de códigos con ERP1 | 100%: mismos 2.184 códigos, sin sobrantes de ningún lado |
| Categoría y Nombre vs ERP1 | Idénticos en las 2.184 filas |
| Marca | Siempre `FISPA` |
| Sin Codigo Proveedor | **1** (`22706A FISPA`) |
| Codigo Proveedor repetido | `120107` (SKU 120103 y 120107) y `M1015` (SKU M1015 y M1023) |
| Categorías distintas | 58 |
| Formatos de Codigo Proveedor | numérico (1.798), número+letra (119), letras+número (103), `X-999` (87), `XX-X999` (54), otros |

## Lista del proveedor (`lista_proveedor.xlsx`)

| Aspecto | Resultado |
|---|---|
| Encabezado | Fila 9 (arriba: título "LISTA DE PRECIOS 1 DE OCTUBRE 2026") |
| Registros | 3.668 |
| Cod.Articulo duplicados | 0 |
| Rubros | 73 |
| Columnas duplicadas | `Cod.Ref.Aux` = `Referencia`, `Cod.Linea` = `Aplicacion`, `Linea.Descripcion` ×2: **idénticas en 3.668/3.668 filas** |
| CodigoBarras | 0 valores EAN-13 numéricos; 3.656/3.668 iguales a Cod.Articulo; 5 vacíos; algunos con caracteres de control (`_x001F_`) |
| Nulos relevantes | Cod.Ref.Aux 199, Aplicacion 32 |
| Importe | Sin ceros ni vacíos |

## Cruce ERP ↔ Lista del proveedor

| Variante de clave | Cruzados | Colisiones |
|---|---|---|
| Exacta | 2.042 | 0 |
| Trim + mayúsculas | 2.042 | 0 |
| Trim + mayúsculas + sin espacios/guiones | 2.042 | 0 |

- Excepciones: **141** códigos que no figuran en la lista y **1** artículo sin código, total
  **142**. Control: 2.042 + 142 = **2.184** ✔.
- Artículos del proveedor que la empresa no vende (excluidos): 3.668 − 2.042 = 1.626.
- Casi-coincidencias, que **no** se cruzan: 9 códigos para los que existe el mismo código con una
  "A" final (ej. `285600` → `285600A`).

## Sitio fispaargentina.com.ar

| Aspecto | Resultado |
|---|---|
| robots.txt | No existe (404) |
| Página por rubro | `catalogo.php?productos=<CodRubro>`, sin paginación (solo importa el número) |
| Producto en la página | `<div class="producto" id="<Cod.Articulo>">` |
| Imagen | `productos/c/<Cod.Articulo>.jpg?v=<n>` (adicionales: `<cod>-1.jpg`) |
| Sin foto | Imagen genérica `imagenes/Fispa_imagen.jpg` |
| Ficha individual | `POST kam/m/_busProductos.php` con `idProd=<cod>`; si no existe devuelve una ficha vacía |
| Resultado del recorrido | 96 páginas de rubro y 11 fichas: 2.026 artículos Fispa con foto, 14 sin foto (3 con imagen genérica y 11 que no están publicados en el sitio) |

## Caracteres rotos en los textos

| Columna | Caso | Filas | Tratamiento (D11) |
|---|---|---|---|
| Categoria (ERP) | `KITS DE FILTROS Y OïRINGS` | 45 | No se toca (inmutable); corregir en el ERP |
| Aplicacion (Fispa) | `O?RINGS` | 32 | Se repara a `O'RINGS` (así lo escribe la web de Fispa) |
| Aplicacion / Cod.Ref.Aux (Fispa) | `?` como separador (`2005 ? 2016`) | 43 + 1 | Se reemplaza por ` - ` |
| Aplicacion / Cod.Ref.Aux | `1? SERIE`, `Salida ?8`, `50?C`, `OHM?` | 29 + 8 | Se deja: el carácter original no se puede determinar |

## Precio de venta frente al costo de reposición

| Aspecto | Resultado |
|---|---|
| Artículos cruzados con precio > 0 | 2.042 |
| Precio menor al costo de reposición de Fispa | **522** (25,6%) |
| Cociente precio / costo | mín 0,88 · mediana 1,01 · máx 1,01 |
| Categorías con más casos | Sensores de rotación (204), Inyectores (133), Sensores ABS (69) |
| Causa | No determinable con estos datos (precios desactualizados o costo de lista antes de descuentos). Se informa como alarma (D12) |
