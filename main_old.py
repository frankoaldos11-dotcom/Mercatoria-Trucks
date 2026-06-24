print("=== MERCATORIA TRUCK v0.1 ===")

cliente = input("Cliente: ")
origen = input("Origen: ")
destino = input("Destino: ")

precio_viaje = float(input("Precio del viaje USD: "))
combustible = float(input("Costo combustible USD: "))
pago_camionero = float(input("Pago camionero USD: "))
porcentaje_comision = float(input("Comisión Mercatoria %: "))

comision = precio_viaje * (porcentaje_comision / 100)
beneficio = precio_viaje - combustible - pago_camionero

print("\n--- RESUMEN DEL VIAJE ---")
print("Cliente:", cliente)
print("Ruta:", origen, "->", destino)
print("Precio cliente:", precio_viaje)
print("Combustible:", combustible)
print("Pago camionero:", pago_camionero)
print("Comisión Mercatoria:", comision)
print("Beneficio bruto:", beneficio)