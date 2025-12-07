from app.models.core_banking import Cliente, Cuenta, Movimiento
from app.extensions import db
from sqlalchemy import func

class AnalyticsService:
    
    # Categorías simples basadas en palabras clave
    CATEGORIES = {
        'ALIMENTACION': ['RESTAURANTE', 'MERCADO', 'SUPER', 'BURGER', 'PIZZA', 'STARBUCKS', 'KFC'],
        'TRANSPORTE': ['UBER', 'CABIFY', 'GASOLINERA', 'PEAJE', 'TAXI', 'METRO'],
        'SERVICIOS': ['LUZ', 'AGUA', 'TELEFONO', 'INTERNET', 'NETFLIX', 'SPOTIFY'],
        'SALUD': ['FARMACIA', 'CLINICA', 'HOSPITAL', 'DOCTOR'],
        'RETIROS': ['CAJERO', 'ATM', 'RETIRO']
    }

    @staticmethod
    def _categorize(glosa):
        glosa_upper = glosa.upper()
        for category, keywords in AnalyticsService.CATEGORIES.items():
            for keyword in keywords:
                if keyword in glosa_upper:
                    return category
        return 'OTROS'

    @staticmethod
    def get_spending_by_category(dni):
        # Buscar cliente
        cliente = Cliente.query.filter_by(dni_ruc=dni).first()
        if not cliente:
            return None

        # Obtener movimientos de DEBITO (Gastos)
        movimientos = db.session.query(Movimiento).join(Cuenta).filter(
            Cuenta.cod_cliente == cliente.cod_cliente,
            Movimiento.tipo_mov == 'D' # Solo débitos
        ).all()

        category_stats = {}

        for mov in movimientos:
            cat = AnalyticsService._categorize(mov.glosa_trx)
            monto = float(mov.monto)
            
            if cat not in category_stats:
                category_stats[cat] = {'total': 0.0, 'count': 0}
            
            category_stats[cat]['total'] += monto
            category_stats[cat]['count'] += 1

        # Formatear para respuesta
        return {
            'dni': dni,
            'total_gastado': sum(item['total'] for item in category_stats.values()),
            'categorias': category_stats
        }
