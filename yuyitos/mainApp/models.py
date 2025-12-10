from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

class Proveedor(models.Model):
    id_proveedor = models.CharField(max_length=3, unique=True, help_text="ID de 3 dígitos (ej: 001)")
    nombre = models.CharField(max_length=200)
    rut = models.CharField(max_length=12, unique=True)
    contacto = models.CharField(max_length=100)
    direccion = models.TextField()
    rubro = models.CharField(max_length=100)

    def clean(self):
        if not self.id_proveedor.isdigit() or len(self.id_proveedor) != 3:
            raise ValidationError({'id_proveedor': 'Debe ser un número de 3 dígitos (ej: 001)'})

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Proveedores"


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=3, unique=True, help_text="Código de 3 dígitos (ej: 001)")

    def clean(self):
        if not self.codigo.isdigit() or len(self.codigo) != 3:
            raise ValidationError({'codigo': 'Debe ser un número de 3 dígitos (ej: 001)'})

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Categorías de Productos"


class Producto(models.Model):
    codigo = models.CharField(max_length=17, unique=True, editable=False, help_text="Generado automáticamente")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.PROTECT)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Precio de compra")
    precio = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio de venta")
    marca = models.CharField(max_length=100, blank=True)
    stock = models.IntegerField(default=0)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    numero_secuencial = models.CharField(max_length=3, editable=False, default='001', help_text="Generado automáticamente")

    def generar_codigo(self):
        """
        Genera el código según especificación:
        999 (ID Proveedor) + 999 (Código Familia) + 99999999 (Fecha Vencimiento) + 999 (Secuencial)
        """
        id_prov = self.proveedor.id_proveedor.zfill(3)
        cod_familia = self.categoria.codigo.zfill(3)
        
        if self.fecha_vencimiento:
            fecha_venc = self.fecha_vencimiento.strftime('%d%m%Y')
        else:
            fecha_venc = '00000000'
        
        ultimo_producto = Producto.objects.filter(
            proveedor=self.proveedor,
            categoria=self.categoria
        ).exclude(pk=self.pk).order_by('-numero_secuencial').first()
        
        if ultimo_producto and ultimo_producto.numero_secuencial:
            try:
                siguiente = int(ultimo_producto.numero_secuencial) + 1
            except:
                siguiente = 1
        else:
            siguiente = 1
        
        num_sec = str(siguiente).zfill(3)
        self.numero_secuencial = num_sec
        
        codigo_completo = f"{id_prov}{cod_familia}{fecha_venc}{num_sec}"
        return codigo_completo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name_plural = "Productos"


class Cliente(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ]

    nombre = models.CharField(max_length=200)
    apellido = models.CharField(max_length=200, default='')
    rut = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=15)
    direccion = models.TextField()
    email = models.EmailField()
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deuda_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.rut}"

    class Meta:
        verbose_name_plural = "Clientes"


class Venta(models.Model):
    TIPO_PAGO_CHOICES = [
        ('contado', 'Contado'),
        ('credito', 'Crédito'),
    ]

    numero_boleta = models.CharField(max_length=10, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    vendedor = models.ForeignKey(User, on_delete=models.PROTECT)
    tipo_pago = models.CharField(max_length=10, choices=TIPO_PAGO_CHOICES)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now)
    estado_credito = models.CharField(
        max_length=20,
        choices=[("PENDIENTE", "PENDIENTE"), ("CANCELADA", "CANCELADA")],
        default="PENDIENTE"
    )

    def __str__(self):
        return f"Boleta {self.numero_boleta} - ${self.total}"

    class Meta:
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class Abono(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="abonos")
    numero_boleta = models.CharField(max_length=10, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        nuevo = self.pk is None
        super().save(*args, **kwargs)

        if nuevo:
            self.cliente.deuda_actual -= self.monto
            self.cliente.save()

            if self.cliente.deuda_actual <= 0:
                self.cliente.deuda_actual = 0
                self.cliente.save()

                ventas_pendientes = Venta.objects.filter(
                    cliente=self.cliente,
                    tipo_pago='credito',
                    estado_credito='PENDIENTE'
                )

                for venta in ventas_pendientes:
                    venta.estado_credito = 'CANCELADA'
                    venta.save()

    def __str__(self):
        return f"Abono {self.cliente.nombre} - ${self.monto}"


class OrdenPedido(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    fecha = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Orden #{self.id} – {self.proveedor.nombre}"

    class Meta:
        verbose_name_plural = "Órdenes de Pedido"


class DetalleOrdenPedido(models.Model):
    orden = models.ForeignKey(OrdenPedido, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio

    def __str__(self):
        return f"{self.producto.nombre} ({self.cantidad} u.)"


class RecepcionProducto(models.Model):
    orden = models.ForeignKey(OrdenPedido, on_delete=models.PROTECT)
    fecha_recepcion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Recepción Orden #{self.orden.id}"

    class Meta:
        verbose_name_plural = "Recepciones"


class DetalleRecepcion(models.Model):
    recepcion = models.ForeignKey(RecepcionProducto, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_recibida = models.IntegerField()

    def __str__(self):
        return f"{self.producto.nombre} recibidos: {self.cantidad_recibida}"