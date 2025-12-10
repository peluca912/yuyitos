from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from mainApp.models import (
    Proveedor, CategoriaProducto, Producto, Cliente,
    Venta, DetalleVenta, OrdenPedido, DetalleOrdenPedido
)
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = 'Carga datos de demostración para la presentación'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('   🚀 CARGANDO DATOS DE DEMOSTRACIÓN'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # 1. USUARIOS
        self.stdout.write('👤 Creando usuarios...')
        
        # Eliminar usuarios existentes para evitar conflictos
        User.objects.filter(username='admin').delete()
        User.objects.filter(username='vendedora').delete()
        
        admin = User.objects.create(
            username='admin',
            is_superuser=True,
            is_staff=True,
            email='admin@yuyitos.cl',
            first_name='Administrador',
            last_name='Sistema'
        )
        admin.set_password('123456')
        admin.save()
        self.stdout.write(self.style.SUCCESS('   ✅ Admin creado (admin/123456)'))

        vendedora = User.objects.create(
            username='vendedora',
            is_superuser=False,
            is_staff=False,
            email='vendedora@yuyitos.cl',
            first_name='Juanita',
            last_name='Yuyitos'
        )
        vendedora.set_password('123456')
        vendedora.save()
        self.stdout.write(self.style.SUCCESS('   ✅ Vendedora creada (vendedora/123456)\n'))

        # 2. PROVEEDORES (3 MÁXIMO)
        self.stdout.write('🚚 Creando proveedores...')
        
        proveedores_data = [
            {'id_proveedor': '001', 'nombre': 'Coca-Cola Chile', 'rut': '12.345.678-9',
             'contacto': 'Juan Pérez', 'direccion': 'Av. Providencia 123, Santiago', 'rubro': 'Bebidas'},
            {'id_proveedor': '002', 'nombre': 'Carozzi S.A.', 'rut': '98.765.432-1',
             'contacto': 'María González', 'direccion': 'Camino Longitudinal Sur 5201, San Bernardo', 'rubro': 'Alimentos'},
            {'id_proveedor': '003', 'nombre': 'Unilever Chile', 'rut': '11.222.333-4',
             'contacto': 'Pedro Soto', 'direccion': 'Av. Kennedy 5757, Las Condes', 'rubro': 'Aseo'},
        ]

        proveedores = {}
        for prov_data in proveedores_data:
            prov, created = Proveedor.objects.get_or_create(
                id_proveedor=prov_data['id_proveedor'],
                defaults=prov_data
            )
            proveedores[prov_data['id_proveedor']] = prov
            if created:
                self.stdout.write(f"   ✅ {prov.nombre}")
        
        self.stdout.write('')

        # 3. CATEGORÍAS (3 MÁXIMO)
        self.stdout.write('📦 Creando categorías...')
        
        categorias_data = [
            {'codigo': '001', 'nombre': 'Bebidas'},
            {'codigo': '002', 'nombre': 'Alimentos'},
            {'codigo': '003', 'nombre': 'Aseo'},
        ]

        categorias = {}
        for cat_data in categorias_data:
            cat, created = CategoriaProducto.objects.get_or_create(
                codigo=cat_data['codigo'],
                defaults=cat_data
            )
            categorias[cat_data['codigo']] = cat
            if created:
                self.stdout.write(f"   ✅ {cat.nombre}")
        
        self.stdout.write('')

        # 4. PRODUCTOS (3 MÁXIMO)
        self.stdout.write('🛒 Creando productos...')
        
        productos_data = [
            {'nombre': 'Coca-Cola 1.5L', 'proveedor': '001', 'categoria': '001',
             'precio_compra': 800, 'precio': 1200, 'stock': 50, 'marca': 'Coca-Cola'},
            {'nombre': 'Arroz Tucapel 1kg', 'proveedor': '002', 'categoria': '002',
             'precio_compra': 900, 'precio': 1400, 'stock': 30, 'marca': 'Tucapel'},
            {'nombre': 'Jabón Dove 90g', 'proveedor': '003', 'categoria': '003',
             'precio_compra': 700, 'precio': 1100, 'stock': 15, 'marca': 'Dove'},
        ]

        productos = []
        for prod_data in productos_data:
            prod_existente = Producto.objects.filter(nombre=prod_data['nombre']).first()
            if not prod_existente:
                prod = Producto(
                    nombre=prod_data['nombre'],
                    proveedor=proveedores[prod_data['proveedor']],
                    categoria=categorias[prod_data['categoria']],
                    precio_compra=prod_data['precio_compra'],
                    precio=prod_data['precio'],
                    stock=prod_data['stock'],
                    marca=prod_data['marca']
                )
                prod.save()
                productos.append(prod)
                stock_color = '🟢' if prod.stock > 30 else '🟡' if prod.stock > 10 else '🔴'
                self.stdout.write(f"   ✅ {prod.nombre} {stock_color} Stock: {prod.stock}")
            else:
                productos.append(prod_existente)
        
        self.stdout.write('')

        # 5. CLIENTES (3 MÁXIMO - TÚ Y TUS AMIGOS)
        self.stdout.write('👥 Creando clientes (Desarrolladores)...')
        
        clientes_data = [
            {'rut': '21.897.212-8', 'nombre': 'Sergio', 'apellido': 'Matus',
             'telefono': '+56912345678', 'direccion': 'Maipú, Santiago',
             'email': 'sergio.matus@duocuc.cl', 'limite_credito': 50000, 'deuda_actual': 0},
            
            {'rut': '21.000.000-1', 'nombre': 'Alexander', 'apellido': 'Martínez',
             'telefono': '+56987654321', 'direccion': 'Maipú, Santiago',
             'email': 'alexander.martinez@duocuc.cl', 'limite_credito': 50000, 'deuda_actual': 0},
            
            {'rut': '21.000.000-2', 'nombre': 'Cristobal', 'apellido': 'Mercedes',
             'telefono': '+56956781234', 'direccion': 'Maipú, Santiago',
             'email': 'cristobal.mercedes@duocuc.cl', 'limite_credito': 50000, 'deuda_actual': 0},
        ]

        clientes = []
        for cli_data in clientes_data:
            cli, created = Cliente.objects.get_or_create(
                rut=cli_data['rut'],
                defaults={**cli_data, 'estado': 'activo'}
            )
            clientes.append(cli)
            if created:
                self.stdout.write(f"   ✅ {cli.nombre} {cli.apellido} ✅ Sin deuda")
        
        self.stdout.write('')

        # 6. VENTAS (3 MÁXIMO)
        self.stdout.write('💰 Creando ventas de ejemplo...')
        
        ventas_data = [
            {
                'numero_boleta': '0000000001',
                'cliente': clientes[0],  # Sergio
                'vendedor': vendedora,
                'tipo_pago': 'contado',
                'estado_credito': 'CANCELADA',
                'items': [
                    {'producto': 0, 'cantidad': 2, 'precio': 1200},  # Coca-Cola
                ]
            },
            {
                'numero_boleta': '0000000002',
                'cliente': clientes[1],  # Alexander
                'vendedor': vendedora,
                'tipo_pago': 'contado',
                'estado_credito': 'CANCELADA',
                'items': [
                    {'producto': 1, 'cantidad': 3, 'precio': 1400},  # Arroz
                ]
            },
            {
                'numero_boleta': '0000000003',
                'cliente': clientes[2],  # Cristobal
                'vendedor': admin,
                'tipo_pago': 'contado',
                'estado_credito': 'CANCELADA',
                'items': [
                    {'producto': 2, 'cantidad': 4, 'precio': 1100},  # Jabón
                ]
            },
        ]

        for venta_data in ventas_data:
            venta_existente = Venta.objects.filter(numero_boleta=venta_data['numero_boleta']).first()
            if not venta_existente:
                total = sum(item['cantidad'] * item['precio'] for item in venta_data['items'])
                
                venta = Venta.objects.create(
                    numero_boleta=venta_data['numero_boleta'],
                    cliente=venta_data['cliente'],
                    vendedor=venta_data['vendedor'],
                    tipo_pago=venta_data['tipo_pago'],
                    total=total,
                    estado_credito=venta_data['estado_credito']
                )
                
                for item in venta_data['items']:
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=productos[item['producto']],
                        cantidad=item['cantidad'],
                        precio_unitario=item['precio'],
                        subtotal=item['cantidad'] * item['precio']
                    )
                
                tipo_icon = '💵' if venta.tipo_pago == 'contado' else '💳'
                self.stdout.write(f"   ✅ Boleta {venta.numero_boleta} {tipo_icon} Cliente: {venta.cliente.nombre}")
        
        self.stdout.write('')

        # 7. ÓRDENES DE PEDIDO (3 MÁXIMO)
        self.stdout.write('📋 Creando órdenes de pedido...')
        
        ordenes_data = [
            {
                'proveedor': '001',
                'producto_idx': 0,  # Coca-Cola
                'cantidad': 30,
                'precio': 800
            },
            {
                'proveedor': '002',
                'producto_idx': 1,  # Arroz
                'cantidad': 20,
                'precio': 900
            },
            {
                'proveedor': '003',
                'producto_idx': 2,  # Jabón
                'cantidad': 25,
                'precio': 700
            },
        ]

        for idx, orden_data in enumerate(ordenes_data, start=1):
            orden_existente = OrdenPedido.objects.filter(id=idx).first()
            if not orden_existente:
                orden = OrdenPedido.objects.create(
                    proveedor=proveedores[orden_data['proveedor']],
                    fecha=timezone.now()
                )
                DetalleOrdenPedido.objects.create(
                    orden=orden,
                    producto=productos[orden_data['producto_idx']],
                    cantidad=orden_data['cantidad'],
                    precio=orden_data['precio']
                )
                self.stdout.write(f"   ✅ Orden #{orden.id} - {orden.proveedor.nombre}")
        
        self.stdout.write('')

        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('   ✅ DATOS CARGADOS EXITOSAMENTE'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('📝 CREDENCIALES DE ACCESO:'))
        self.stdout.write(self.style.WARNING('   ─────────────────────────────'))
        self.stdout.write('   👤 Admin:     admin / 123456')
        self.stdout.write('   👤 Vendedora: vendedora / 123456')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN:'))
        self.stdout.write(self.style.SUCCESS('   ─────────────────────────────'))
        self.stdout.write(f"   • Proveedores: {Proveedor.objects.count()}")
        self.stdout.write(f"   • Categorías:  {CategoriaProducto.objects.count()}")
        self.stdout.write(f"   • Productos:   {Producto.objects.count()}")
        self.stdout.write(f"   • Clientes:    {Cliente.objects.count()}")
        self.stdout.write(f"   • Ventas:      {Venta.objects.count()}")
        self.stdout.write(f"   • Órdenes:     {OrdenPedido.objects.count()}")
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('👨‍💻 DESARROLLADORES:'))
        self.stdout.write(self.style.SUCCESS('   ─────────────────────────────'))
        self.stdout.write('   • Sergio Matus')
        self.stdout.write('   • Alexander Martínez')
        self.stdout.write('   • Cristobal Mercedes')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('   🚀 ¡LISTO PARA LA PRESENTACIÓN!'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))