from django.contrib import admin
from .models import (
    Proveedor, CategoriaProducto, Producto, Cliente, 
    Venta, DetalleVenta, Abono, OrdenPedido, 
    DetalleOrdenPedido, RecepcionProducto, DetalleRecepcion
)

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['id_proveedor', 'nombre', 'rut', 'contacto', 'rubro']
    search_fields = ['nombre', 'rut', 'id_proveedor']

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo']
    search_fields = ['nombre', 'codigo']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'marca', 'precio_compra', 'precio', 'stock', 'proveedor', 'categoria']
    list_filter = ['categoria', 'proveedor', 'marca']
    search_fields = ['codigo', 'nombre', 'marca']
    readonly_fields = ['codigo', 'numero_secuencial']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'rut', 'deuda_actual', 'estado']
    list_filter = ['estado']
    search_fields = ['nombre', 'apellido', 'rut']

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ['subtotal']

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['numero_boleta', 'cliente', 'fecha', 'vendedor', 'tipo_pago', 'total', 'estado_credito']
    list_filter = ['tipo_pago', 'estado_credito', 'fecha']
    search_fields = ['numero_boleta', 'cliente__nombre']
    inlines = [DetalleVentaInline]

@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'numero_boleta', 'monto', 'fecha']
    list_filter = ['fecha']
    search_fields = ['cliente__nombre', 'numero_boleta']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

@admin.register(OrdenPedido)
class OrdenPedidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'proveedor', 'fecha']
    list_filter = ['fecha', 'proveedor']

@admin.register(RecepcionProducto)
class RecepcionProductoAdmin(admin.ModelAdmin):
    list_display = ['id', 'orden', 'fecha_recepcion']
    list_filter = ['fecha_recepcion']