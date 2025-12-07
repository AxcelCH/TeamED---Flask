from app.models.core_banking import Cliente, Cuenta, Tarjeta, Movimiento
from app.extensions import db

class ClientService:
    @staticmethod
    def get_client_by_dni(dni):
        return Cliente.query.filter_by(dni_ruc=dni).first()

    @staticmethod
    def get_products(dni):
        cliente = ClientService.get_client_by_dni(dni)
        if not cliente:
            return None

        # Obtener cuentas
        cuentas = Cuenta.query.filter_by(cod_cliente=cliente.cod_cliente).all()
        cuentas_data = [{
            'num_cuenta': c.num_cuenta,
            'tipo_cuenta': c.tipo_cuenta,
            'moneda': c.moneda,
            'saldo_disponible': float(c.saldo_disponible),
            'estado': c.estado
        } for c in cuentas]

        # Obtener tarjetas
        tarjetas = Tarjeta.query.filter_by(cod_cliente=cliente.cod_cliente).all()
        tarjetas_data = [{
            'num_tarjeta': c.num_tarjeta, # Considerar enmascarar si es para frontend
            'tipo_tarjeta': c.tipo_tarjeta,
            'marca': c.marca,
            'fecha_venc': c.fecha_venc.strftime('%Y-%m-%d'),
            'estado': c.estado
        } for c in tarjetas]

        return {
            'cliente': {
                'nombres': cliente.nombres,
                'apellidos': cliente.apellidos,
                'dni': cliente.dni_ruc
            },
            'cuentas': cuentas_data,
            'tarjetas': tarjetas_data
        }

    @staticmethod
    def get_transactions(dni):
        cliente = ClientService.get_client_by_dni(dni)
        if not cliente:
            return None

        # Obtener movimientos de todas las cuentas del cliente
        # Join Movimiento con Cuenta
        movimientos = db.session.query(Movimiento).join(Cuenta).filter(Cuenta.cod_cliente == cliente.cod_cliente).order_by(Movimiento.fecha_proceso.desc()).all()

        return [{
            'id_trx': m.id_trx,
            'fecha': m.fecha_proceso.strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': m.tipo_mov,
            'monto': float(m.monto),
            'moneda': m.moneda,
            'glosa': m.glosa_trx,
            'canal': m.cod_canal,
            'cuenta_origen': m.num_cuenta
        } for m in movimientos]
