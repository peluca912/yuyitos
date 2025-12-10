from django.contrib import admin
from django.urls import path
from mainApp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),

    path('home/', views.home, name="home"),

    path('productos/', views.productos, name="productos"),
    path('inventario/', views.inventario, name="inventario"),

    path('ventas/', views.ventas, name="ventas"),
    path('ventas/registrar/', views.registrar_venta, name="registrar_venta"),
    path('ventas/<int:venta_id>/', views.detalle_venta, name="detalle_venta"),
    
    path('clientes/', views.clientes, name="clientes"),
    path('clientes/<int:cliente_id>/ficha-credito/', views.ficha_credito, name="ficha_credito"),
    
    path('ordenes-pedido/', views.ordenes_pedido, name="ordenes_pedido"),
    path('ordenes-pedido/crear/', views.crear_orden_pedido, name="crear_orden_pedido"),
    path('ordenes-pedido/<int:orden_id>/', views.detalle_orden_pedido, name="detalle_orden_pedido"),
    
    path('recepciones/', views.recepciones, name="recepciones"),
    path('recepciones/crear/<int:orden_id>/', views.crear_recepcion, name="crear_recepcion"),
    path('recepciones/<int:recepcion_id>/', views.detalle_recepcion, name="detalle_recepcion"),
    
    path('api/productos-proveedor/<int:proveedor_id>/', views.api_productos_proveedor, name="api_productos_proveedor"),
    
    path('productos/<int:producto_id>/codigo-barra/', views.imprimir_codigo_barra, name="imprimir_codigo_barra"),
]