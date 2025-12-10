from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    Producto, Venta, Cliente, Proveedor, DetalleVenta,
    CategoriaProducto, Abono, OrdenPedido, DetalleOrdenPedido,
    RecepcionProducto, DetalleRecepcion
)


# -----------------------------
# ROLES
# -----------------------------
def es_admin(user):
    return user.is_superuser


def es_vendedor(user):
    return not user.is_superuser


# -----------------------------
# LOGIN CON REDIRECCIÓN Y MENSAJE CORREGIDO
# -----------------------------
def login_view(request):
    # SI YA ESTÁ AUTENTICADO, REDIRIGIR
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('home')
        else:
            return redirect('ventas')
    
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # MENSAJE DE BIENVENIDA CORREGIDO (sin duplicar rol)
            if user.is_superuser:
                messages.success(request, f"✅ ¡Bienvenido, {user.username}!")
                return redirect('home')
            else:
                messages.success(request, f"✅ ¡Bienvenida, {user.username}!")
                return redirect('ventas')

        # MENSAJE DE ERROR MEJORADO
        messages.error(request, "❌ Usuario o contraseña incorrectos. Por favor, verifica tus datos.")
        return redirect('login')

    return render(request, "login.html")


# -----------------------------
# LOGOUT
# -----------------------------
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "✅ Has cerrado sesión exitosamente.")
    return redirect('login')


# -----------------------------
# HOME – SOLO ADMIN
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/ventas/')
def home(request):
    # Estadísticas generales
    total_productos = Producto.objects.count()
    total_ventas = Venta.objects.count()
    productos_bajo_stock = Producto.objects.filter(stock__lt=10).count()
    total_clientes = Cliente.objects.count()
    total_proveedores = Proveedor.objects.count()
    
    # Ventas del mes actual
    hoy = timezone.now()
    inicio_mes = hoy.replace(day=1)
    ventas_mes = Venta.objects.filter(fecha__gte=inicio_mes).aggregate(
        total=Sum('total')
    )['total'] or 0
    
    context = {
        'total_productos': total_productos,
        'total_ventas': total_ventas,
        'productos_bajo_stock': productos_bajo_stock,
        'total_clientes': total_clientes,
        'total_proveedores': total_proveedores,
        'ventas_mes': ventas_mes,
    }
    return render(request, "home.html", context)


# -----------------------------
# PRODUCTOS – ADMIN Y VENDEDOR
# -----------------------------
@login_required
def productos(request):
    query = request.GET.get('q', '')
    lista = Producto.objects.all()
    
    if query:
        lista = lista.filter(nombre__icontains=query) | lista.filter(codigo__icontains=query)
    
    return render(request, "productos.html", {"productos": lista, "query": query})


# -----------------------------
# INVENTARIO – SOLO ADMIN
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/')
def inventario(request):
    lista = Producto.objects.all().order_by('stock')
    return render(request, "inventario.html", {"productos": lista})


# -----------------------------
# VENTAS – ADMIN Y VENDEDOR
# -----------------------------
@login_required
def ventas(request):
    # Si es vendedor, solo ve sus propias ventas
    if request.user.is_superuser:
        lista = Venta.objects.all().order_by('-fecha')[:20]
    else:
        lista = Venta.objects.filter(vendedor=request.user).order_by('-fecha')[:20]
    
    return render(request, "ventas.html", {"ventas": lista})


# -----------------------------
# REGISTRAR VENTA
# -----------------------------
@login_required
def registrar_venta(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # Validaciones básicas de entrada
            if not data.get('items') or len(data['items']) == 0:
                return JsonResponse({'success': False, 'error': 'Debe agregar al menos un producto.'}, status=400)

            # Cliente obligatorio siempre (backend)
            cliente_id = data.get('cliente_id')
            if not cliente_id:
                return JsonResponse({'success': False, 'error': 'Debe seleccionar un cliente.'}, status=400)

            try:
                cliente = Cliente.objects.get(id=cliente_id)
            except Cliente.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Cliente no encontrado.'}, status=400)

            with transaction.atomic():
                # Generar número de boleta (igual que tu lógica original)
                ultima_venta = Venta.objects.all().order_by('-id').first()
                if ultima_venta and ultima_venta.numero_boleta:
                    try:
                        ultimo_numero = int(ultima_venta.numero_boleta)
                    except ValueError:
                        ultimo_numero = 0
                    nuevo_numero = str(ultimo_numero + 1).zfill(10)
                else:
                    nuevo_numero = "0000000001"

                total_enviado = Decimal(str(data.get('total', '0')))

                # Crear venta
                venta = Venta.objects.create(
                    numero_boleta=nuevo_numero,
                    cliente=cliente,
                    vendedor=request.user,
                    tipo_pago=data.get('tipo_pago'),
                    total=total_enviado
                )

                # Crear detalles y actualizar stock
                for item in data['items']:
                    producto_id = item.get('producto_id')
                    cantidad = int(item.get('cantidad', 0))
                    if cantidad <= 0:
                        raise Exception('Cantidad inválida para un producto.')

                    try:
                        producto = Producto.objects.get(id=producto_id)
                    except Producto.DoesNotExist:
                        raise Exception('Producto no encontrado.')

                    if producto.stock < cantidad:
                        raise Exception(f"Stock insuficiente para {producto.nombre} (disponible {producto.stock}).")

                    subtotal = Decimal(cantidad) * producto.precio

                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio,
                        subtotal=subtotal
                    )

                    producto.stock -= cantidad
                    producto.save()

                # Si es crédito, actualizar deuda
                if data.get('tipo_pago') == 'credito':
                    cliente.deuda_actual += total_enviado
                    cliente.save()

                return JsonResponse({
                    'success': True,
                    'numero_boleta': nuevo_numero,
                    'message': f'✅ Venta registrada exitosamente. Boleta N° {nuevo_numero}'
                })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # GET: Mostrar formulario
    productos = Producto.objects.filter(stock__gt=0).order_by('nombre')
    clientes = Cliente.objects.filter(estado='activo').order_by('nombre')

    return render(request, "registrar_venta.html", {
        'productos': productos,
        'clientes': clientes
    })


# -----------------------------
# CLIENTES – TODOS CON BÚSQUEDA
# -----------------------------
@login_required
def clientes(request):
    query = request.GET.get('q', '')
    lista = Cliente.objects.all().order_by('nombre')
    
    if query:
        lista = lista.filter(
            Q(nombre__icontains=query) | Q(rut__icontains=query)
        )
    
    return render(request, "clientes.html", {
        "clientes": lista,
        "query": query
    })


# -----------------------------
# DETALLE DE VENTA
# -----------------------------
@login_required
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    
    # Si es vendedor, solo puede ver sus propias ventas
    if not request.user.is_superuser and venta.vendedor != request.user:
        messages.error(request, "No tienes permiso para ver esta venta")
        return redirect('ventas')
    
    detalles = venta.detalles.all()
    
    return render(request, "detalles_venta.html", {
        'venta': venta,
        'detalles': detalles
    })


# -----------------------------
# ÓRDENES DE PEDIDO
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/')
def ordenes_pedido(request):
    """Lista todas las órdenes de pedido"""
    ordenes = OrdenPedido.objects.all().select_related('proveedor').order_by('-fecha')
    return render(request, "ordenes_pedido.html", {"ordenes": ordenes})


@login_required
@user_passes_test(es_admin, login_url='/')
def crear_orden_pedido(request):
    """Crear una nueva orden de pedido"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            proveedor_id = data.get('proveedor_id')
            if not proveedor_id:
                return JsonResponse({'success': False, 'error': 'Debe seleccionar un proveedor.'}, status=400)
            
            if not data.get('items') or len(data['items']) == 0:
                return JsonResponse({'success': False, 'error': 'Debe agregar al menos un producto.'}, status=400)
            
            try:
                proveedor = Proveedor.objects.get(id=proveedor_id)
            except Proveedor.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Proveedor no encontrado.'}, status=400)
            
            with transaction.atomic():
                # Crear orden de pedido
                orden = OrdenPedido.objects.create(proveedor=proveedor)
                
                # Crear detalles
                for item in data['items']:
                    producto_id = item.get('producto_id')
                    cantidad = int(item.get('cantidad', 0))
                    precio = Decimal(str(item.get('precio', 0)))
                    
                    if cantidad <= 0:
                        raise Exception('Cantidad inválida para un producto.')
                    
                    if precio < 0:
                        raise Exception('Precio inválido para un producto.')
                    
                    try:
                        producto = Producto.objects.get(id=producto_id)
                    except Producto.DoesNotExist:
                        raise Exception('Producto no encontrado.')
                    
                    # Verificar que el producto pertenece al proveedor seleccionado
                    if producto.proveedor_id != proveedor.id:
                        raise Exception(f'El producto {producto.nombre} no pertenece al proveedor {proveedor.nombre}.')
                    
                    DetalleOrdenPedido.objects.create(
                        orden=orden,
                        producto=producto,
                        cantidad=cantidad,
                        precio=precio
                    )
                
                return JsonResponse({
                    'success': True,
                    'orden_id': orden.id,
                    'message': f'✅ Orden de pedido #{orden.id} creada exitosamente'
                })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # GET: Mostrar formulario
    proveedores = Proveedor.objects.all().order_by('nombre')
    productos = Producto.objects.all().order_by('nombre')
    
    return render(request, "crear_orden_pedido.html", {
        'proveedores': proveedores,
        'productos': productos
    })


@login_required
@user_passes_test(es_admin, login_url='/')
def detalle_orden_pedido(request, orden_id):
    """Ver detalle de una orden de pedido"""
    orden = get_object_or_404(OrdenPedido, id=orden_id)
    detalles = orden.detalles.all().select_related('producto')
    
    # Calcular total
    total = sum(d.subtotal() for d in detalles)
    
    # Verificar si tiene recepción
    tiene_recepcion = RecepcionProducto.objects.filter(orden=orden).exists()
    
    return render(request, "detalle_orden_pedido.html", {
        'orden': orden,
        'detalles': detalles,
        'total': total,
        'tiene_recepcion': tiene_recepcion
    })


# -----------------------------
# RECEPCIÓN DE PRODUCTOS
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/')
def recepciones(request):
    """Lista todas las recepciones de productos"""
    recepciones = RecepcionProducto.objects.all().select_related('orden', 'orden__proveedor').order_by('-fecha_recepcion')
    return render(request, "recepciones.html", {"recepciones": recepciones})


@login_required
@user_passes_test(es_admin, login_url='/')
def crear_recepcion(request, orden_id):
    """Crear una recepción basada en una orden de pedido"""
    orden = get_object_or_404(OrdenPedido, id=orden_id)
    
    # Verificar si ya existe una recepción para esta orden
    if RecepcionProducto.objects.filter(orden=orden).exists():
        messages.error(request, "❌ Esta orden ya tiene una recepción registrada.")
        return redirect('detalle_orden_pedido', orden_id=orden_id)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            if not data.get('items') or len(data['items']) == 0:
                return JsonResponse({'success': False, 'error': 'Debe ingresar al menos un producto recibido.'}, status=400)
            
            with transaction.atomic():
                # Crear recepción
                recepcion = RecepcionProducto.objects.create(orden=orden)
                
                # Obtener todos los productos de la orden
                productos_orden = {d.producto_id: d for d in orden.detalles.all()}
                
                # Procesar cada item recibido
                for item in data['items']:
                    producto_id = int(item.get('producto_id'))
                    cantidad_recibida = int(item.get('cantidad_recibida', 0))
                    
                    if cantidad_recibida <= 0:
                        raise Exception('Cantidad recibida debe ser mayor a 0.')
                    
                    # VALIDACIÓN: Verificar que el producto está en la orden
                    if producto_id not in productos_orden:
                        try:
                            producto_nombre = Producto.objects.get(id=producto_id).nombre
                        except:
                            producto_nombre = f"ID {producto_id}"
                        raise Exception(f'El producto {producto_nombre} NO está en la orden de pedido #{orden.id}.')
                    
                    detalle_orden = productos_orden[producto_id]
                    
                    # VALIDACIÓN: Verificar que no exceda la cantidad ordenada
                    if cantidad_recibida > detalle_orden.cantidad:
                        raise Exception(
                            f'Cantidad recibida ({cantidad_recibida}) excede la cantidad ordenada '
                            f'({detalle_orden.cantidad}) para {detalle_orden.producto.nombre}.'
                        )
                    
                    # Crear detalle de recepción
                    DetalleRecepcion.objects.create(
                        recepcion=recepcion,
                        producto=detalle_orden.producto,
                        cantidad_recibida=cantidad_recibida
                    )
                    
                    # Actualizar stock del producto
                    producto = detalle_orden.producto
                    producto.stock += cantidad_recibida
                    producto.save()
                
                return JsonResponse({
                    'success': True,
                    'recepcion_id': recepcion.id,
                    'message': f'✅ Recepción #{recepcion.id} registrada exitosamente. Stock actualizado.'
                })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # GET: Mostrar formulario
    detalles_orden = orden.detalles.all().select_related('producto')
    
    return render(request, "crear_recepcion.html", {
        'orden': orden,
        'detalles_orden': detalles_orden
    })


@login_required
@user_passes_test(es_admin, login_url='/')
def detalle_recepcion(request, recepcion_id):
    """Ver detalle de una recepción de productos"""
    recepcion = get_object_or_404(RecepcionProducto, id=recepcion_id)
    detalles = recepcion.detalles.all().select_related('producto')
    detalles_orden = recepcion.orden.detalles.all().select_related('producto')
    
    # Crear un diccionario para comparar cantidades ordenadas vs recibidas
    comparacion = []
    for detalle_orden in detalles_orden:
        cantidad_recibida = 0
        detalle_recepcion = detalles.filter(producto=detalle_orden.producto).first()
        if detalle_recepcion:
            cantidad_recibida = detalle_recepcion.cantidad_recibida
        
        comparacion.append({
            'producto': detalle_orden.producto,
            'cantidad_ordenada': detalle_orden.cantidad,
            'cantidad_recibida': cantidad_recibida,
            'diferencia': cantidad_recibida - detalle_orden.cantidad,
            'completo': cantidad_recibida == detalle_orden.cantidad
        })
    
    return render(request, "detalle_recepcion.html", {
        'recepcion': recepcion,
        'comparacion': comparacion
    })


# -----------------------------
# API: OBTENER PRODUCTOS POR PROVEEDOR
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/')
def api_productos_proveedor(request, proveedor_id):
    """API para obtener productos de un proveedor específico"""
    try:
        productos = Producto.objects.filter(proveedor_id=proveedor_id).values(
            'id', 'codigo', 'nombre', 'precio', 'stock'
        )
        return JsonResponse({'success': True, 'productos': list(productos)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# -----------------------------
# FICHA DE CRÉDITO
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/')
def ficha_credito(request, cliente_id):
    """Vista para mostrar la ficha de crédito del cliente"""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    ventas_credito = Venta.objects.filter(
        cliente=cliente,
        tipo_pago='credito'
    ).order_by('-fecha')
    
    abonos = Abono.objects.filter(cliente=cliente).order_by('-fecha')
    
    return render(request, "ficha_credito.html", {
        'cliente': cliente,
        'ventas_credito': ventas_credito,
        'abonos': abonos
    })


# -----------------------------
# IMPRIMIR CÓDIGO DE BARRA (VERSIÓN HTML)
# -----------------------------
@login_required
@user_passes_test(es_admin, login_url='/')
def imprimir_codigo_barra(request, producto_id):
    """Vista HTML para imprimir código de producto"""
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, "imprimir_codigo.html", {'producto': producto})