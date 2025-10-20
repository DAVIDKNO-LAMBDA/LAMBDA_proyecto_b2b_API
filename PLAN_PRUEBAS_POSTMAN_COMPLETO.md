# 🧪 **PLAN COMPLETO DE PRUEBAS POSTMAN - SISTEMA B2B LAMBDA**

## 📋 **CONFIGURACIÓN INICIAL**

### 🔧 **1. Variables de Entorno en Postman**

Crear un **Environment** en Postman llamado `B2B_Lambda_Test` con estas variables:

```json
{
    "base_url": "http://localhost:8000",
    "admin_lambda_email": "admin@lambda.com",
    "admin_lambda_password": "Lambda123!",
    "admin_empresa_email": "admin@tecnofuturo.com",
    "admin_empresa_password": "TecnoFuturo123!",
    "jefe_area_email": "jefe.sistemas@tecnofuturo.com",
    "jefe_area_password": "JefeSistemas123!",
    "validador_abast_empresa_email": "abastecimiento@tecnofuturo.com",
    "validador_abast_empresa_password": "Abast123!",
    "validador_fin_empresa_email": "finanzas@tecnofuturo.com",
    "validador_fin_empresa_password": "Finanzas123!",
    "validador_abast_lambda_email": "abastecimiento@lambda.com",
    "validador_abast_lambda_password": "AbastLambda123!",
    "validador_fin_lambda_email": "finanzas@lambda.com",
    "validador_fin_lambda_password": "FinLambda123!",
    "admin_lambda_token": "",
    "admin_empresa_token": "",
    "jefe_area_token": "",
    "validador_abast_empresa_token": "",
    "validador_fin_empresa_token": "",
    "validador_abast_lambda_token": "",
    "validador_fin_lambda_token": "",
    "empresa_id": "",
    "area_sistemas_id": "",
    "area_compras_id": "",
    "producto_laptop_id": "",
    "producto_servidor_id": "",
    "solicitud_id": "",
    "pedido_id": ""
}
```

### 🚀 **2. Comandos de Preparación**

**Antes de empezar las pruebas, ejecutar en terminal:**

```bash
# 1. Activar entorno virtual
cd "C:\Users\Jorman\Desktop\LAMBDA_proyecto_b2b_API"
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones
python manage.py migrate

# 4. Crear roles y permisos
python manage.py bootstrap_roles

# 5. Iniciar servidor
python manage.py runserver
```

---

## 🧪 **SUITE DE PRUEBAS POSTMAN**

### 📁 **COLECCIÓN 1: AUTENTICACIÓN Y CONFIGURACIÓN INICIAL**

#### **Test 1.1: Crear Admin Lambda**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Content-Type: application/json

{
    "email": "{{admin_lambda_email}}",
    "nombres": "David",
    "apellidos": "Administrador Lambda",
    "cargo": "Admin Lambda",
    "password": "{{admin_lambda_password}}",
    "is_staff": true,
    "empresa": null
}
```

**Pre-script:**
```javascript
// Guardar token si existe
pm.environment.set("admin_lambda_token", "");
```

**Tests:**
```javascript
pm.test("Admin Lambda creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property("id");
    pm.environment.set("admin_lambda_id", response.id);
});
```

---

#### **Test 1.2: Login Admin Lambda**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{admin_lambda_email}}",
    "password": "{{admin_lambda_password}}"
}
```

**Tests:**
```javascript
pm.test("Login Admin Lambda exitoso", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response).to.have.property("access");
    pm.environment.set("admin_lambda_token", response.access);
});
```

---

### 📁 **COLECCIÓN 2: GESTIÓN DE EMPRESAS (HU01-HU03)**

#### **Test 2.1: Crear Empresa Cliente**
```http
POST {{base_url}}/api/empresas/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "nit": "900123456-7",
    "razon_social": "Tecnologías del Futuro S.A.",
    "nombre_comercial": "TecnoFuturo",
    "correo_contacto": "{{admin_empresa_email}}",
    "telefono": "+57 1 234-5678",
    "direccion": "Calle 100 # 15-20, Bogotá",
    "ciudad": "Bogotá",
    "departamento": "Cundinamarca",
    "pais": "Colombia",
    "tipo_empresa": "tecnologia",
    "estado": "activa",
    "puede_pagar_despues": true
}
```

**Tests:**
```javascript
pm.test("Empresa creada correctamente", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property("id");
    pm.environment.set("empresa_id", response.id);
});
```

---

#### **Test 2.2: Listar Empresas**
```http
GET {{base_url}}/api/empresas/
Authorization: Bearer {{admin_lambda_token}}
```

**Tests:**
```javascript
pm.test("Listado de empresas", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.results).to.be.an('array');
    pm.expect(response.results.length).to.be.greaterThan(0);
});
```

---

### 📁 **COLECCIÓN 3: GESTIÓN DE USUARIOS Y ROLES (HU04-HU09)**

#### **Test 3.1: Crear Admin Empresa**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "email": "{{admin_empresa_email}}",
    "nombres": "Carlos Alberto",
    "apellidos": "Rodriguez Mendez",
    "cargo": "Gerente General",
    "empresa": "{{empresa_id}}",
    "password": "{{admin_empresa_password}}",
    "es_primer_usuario": true
}
```

**Tests:**
```javascript
pm.test("Admin Empresa creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("admin_empresa_id", response.id);
});
```

---

#### **Test 3.2: Asignar Rol Admin Empresa**
```http
POST {{base_url}}/api/usuarios/{{admin_empresa_id}}/asignar-rol/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "grupo": "Admin Empresa"
}
```

**Tests:**
```javascript
pm.test("Rol Admin Empresa asignado", function () {
    pm.response.to.have.status(200);
});
```

---

#### **Test 3.3: Login Admin Empresa**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{admin_empresa_email}}",
    "password": "{{admin_empresa_password}}"
}
```

**Tests:**
```javascript
pm.test("Login Admin Empresa exitoso", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.environment.set("admin_empresa_token", response.access);
});
```

---

### 📁 **COLECCIÓN 4: CREACIÓN DE ÁREAS (HU08)**

#### **Test 4.1: Crear Área Sistemas**
```http
POST {{base_url}}/api/areas/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "nombre": "Sistemas e Infraestructura",
    "descripcion": "Área encargada de tecnología y sistemas",
    "empresa": "{{empresa_id}}"
}
```

**Tests:**
```javascript
pm.test("Área Sistemas creada", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("area_sistemas_id", response.id);
});
```

---

#### **Test 4.2: Crear Área Compras**
```http
POST {{base_url}}/api/areas/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "nombre": "Compras y Abastecimiento",
    "descripcion": "Área encargada de adquisiciones",
    "empresa": "{{empresa_id}}"
}
```

**Tests:**
```javascript
pm.test("Área Compras creada", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("area_compras_id", response.id);
});
```

---

### 📁 **COLECCIÓN 5: CREACIÓN DE EMPLEADOS**

#### **Test 5.1: Crear Jefe de Área Sistemas**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "email": "{{jefe_area_email}}",
    "nombres": "María Elena",
    "apellidos": "Gómez Silva",
    "cargo": "Jefe de Sistemas",
    "empresa": "{{empresa_id}}",
    "area": "{{area_sistemas_id}}",
    "password": "{{jefe_area_password}}",
    "es_jefe_area": true
}
```

**Tests:**
```javascript
pm.test("Jefe de Área creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("jefe_area_id", response.id);
});
```

---

#### **Test 5.2: Asignar Rol Jefe de Área**
```http
POST {{base_url}}/api/usuarios/{{jefe_area_id}}/asignar-rol/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "grupo": "Jefe de Área"
}
```

---

#### **Test 5.3: Crear Validador Abastecimiento Empresa**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "email": "{{validador_abast_empresa_email}}",
    "nombres": "Ana",
    "apellidos": "Validadora Abastecimiento",
    "cargo": "Coordinadora de Abastecimiento",
    "empresa": "{{empresa_id}}",
    "area": "{{area_compras_id}}",
    "password": "{{validador_abast_empresa_password}}"
}
```

**Tests:**
```javascript
pm.test("Validador Abastecimiento Empresa creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("validador_abast_empresa_id", response.id);
});
```

---

#### **Test 5.4: Asignar Rol y Permisos Validador Abastecimiento**
```http
POST {{base_url}}/api/usuarios/{{validador_abast_empresa_id}}/asignar-rol/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "grupo": "Validador Abastecimiento"
}
```

---

#### **Test 5.5: Asignar Permisos Especiales Abastecimiento**
```http
POST {{base_url}}/api/usuarios/{{validador_abast_empresa_id}}/permisos-especiales/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "permisos": {
        "validador_abastecimiento": true,
        "puede_crear_solicitudes": true
    }
}
```

---

#### **Test 5.6: Crear Validador Finanzas Empresa**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "email": "{{validador_fin_empresa_email}}",
    "nombres": "Luis",
    "apellidos": "Validador Finanzas",
    "cargo": "Coordinador Financiero",
    "empresa": "{{empresa_id}}",
    "area": "{{area_compras_id}}",
    "password": "{{validador_fin_empresa_password}}"
}
```

**Tests:**
```javascript
pm.test("Validador Finanzas Empresa creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("validador_fin_empresa_id", response.id);
});
```

---

#### **Test 5.7: Asignar Rol y Permisos Validador Finanzas**
```http
POST {{base_url}}/api/usuarios/{{validador_fin_empresa_id}}/asignar-rol/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "grupo": "Validador Financiero"
}
```

---

#### **Test 5.8: Asignar Permisos Especiales Finanzas**
```http
POST {{base_url}}/api/usuarios/{{validador_fin_empresa_id}}/permisos-especiales/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "permisos": {
        "validador_finanzas": true,
        "puede_crear_solicitudes": true,
        "limite_aprobacion": 100000000
    }
}
```

---

### 📁 **COLECCIÓN 6: LOGIN DE TODOS LOS USUARIOS**

#### **Test 6.1: Login Jefe de Área**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{jefe_area_email}}",
    "password": "{{jefe_area_password}}"
}
```

**Tests:**
```javascript
pm.test("Login Jefe de Área exitoso", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.environment.set("jefe_area_token", response.access);
});
```

---

#### **Test 6.2: Login Validador Abastecimiento Empresa**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{validador_abast_empresa_email}}",
    "password": "{{validador_abast_empresa_password}}"
}
```

**Tests:**
```javascript
pm.test("Login Validador Abastecimiento exitoso", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.environment.set("validador_abast_empresa_token", response.access);
});
```

---

#### **Test 6.3: Login Validador Finanzas Empresa**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{validador_fin_empresa_email}}",
    "password": "{{validador_fin_empresa_password}}"
}
```

**Tests:**
```javascript
pm.test("Login Validador Finanzas exitoso", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.environment.set("validador_fin_empresa_token", response.access);
});
```

---

### 📁 **COLECCIÓN 7: CATÁLOGO DE PRODUCTOS (HU23)**

#### **Test 7.1: Crear Producto Laptop**
```http
POST {{base_url}}/api/productos/crear/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "nombre": "Laptop Dell Latitude 7420",
    "descripcion": "Laptop empresarial de alto rendimiento",
    "precio": 3500000.00,
    "categoria": "Equipos de Cómputo",
    "unidad_medida": "Unidad",
    "stock_disponible": 10,
    "stock_minimo": 3,
    "estado": "activo"
}
```

**Tests:**
```javascript
pm.test("Producto Laptop creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("producto_laptop_id", response.id);
});
```

---

#### **Test 7.2: Crear Producto Servidor**
```http
POST {{base_url}}/api/productos/crear/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "nombre": "Servidor HP ProLiant DL380",
    "descripcion": "Servidor empresarial para centro de datos",
    "precio": 15000000.00,
    "categoria": "Servidores",
    "unidad_medida": "Unidad",
    "stock_disponible": 5,
    "stock_minimo": 1,
    "estado": "activo"
}
```

**Tests:**
```javascript
pm.test("Producto Servidor creado", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.environment.set("producto_servidor_id", response.id);
});
```

---

### 📁 **COLECCIÓN 8: FLUJO COMPLETO DE SOLICITUD (HU10-HU13)**

#### **Test 8.1: Crear Solicitud (HU10)**
```http
POST {{base_url}}/api/solicitudes/crear/
Authorization: Bearer {{jefe_area_token}}
Content-Type: application/json

{
    "titulo": "Equipos de cómputo para nuevo proyecto",
    "justificacion": "Necesitamos equipos para el proyecto de migración a la nube",
    "fecha_necesaria": "2025-11-15",
    "area_solicitante": "{{area_sistemas_id}}",
    "productos": [
        {
            "producto": "{{producto_laptop_id}}",
            "cantidad": 3,
            "observaciones": "Para desarrolladores senior"
        },
        {
            "producto": "{{producto_servidor_id}}",
            "cantidad": 1,
            "observaciones": "Para ambiente de testing"
        }
    ]
}
```

**Tests:**
```javascript
pm.test("Solicitud creada correctamente", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property("id");
    pm.expect(response.estado).to.equal("pendiente_jefe_area");
    pm.environment.set("solicitud_id", response.id);
});
```

---

#### **Test 8.2: Aprobar por Jefe de Área**
```http
POST {{base_url}}/api/solicitudes/{{solicitud_id}}/aprobar-jefe/
Authorization: Bearer {{jefe_area_token}}
Content-Type: application/json

{
    "comentario": "Aprobado. Los equipos son necesarios para el proyecto con Bancolombia."
}
```

**Tests:**
```javascript
pm.test("Solicitud aprobada por jefe", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.solicitud.estado).to.equal("pendiente_abastecimiento");
});
```

---

#### **Test 8.3: Listar Solicitudes Pendientes Abastecimiento**
```http
GET {{base_url}}/api/solicitudes/pendientes-abastecimiento/
Authorization: Bearer {{validador_abast_empresa_token}}
```

**Tests:**
```javascript
pm.test("Lista de solicitudes pendientes abastecimiento", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.results).to.be.an('array');
    pm.expect(response.results.length).to.be.greaterThan(0);
});
```

---

#### **Test 8.4: Validar Abastecimiento Empresa (HU12)**
```http
POST {{base_url}}/api/solicitudes/{{solicitud_id}}/validar-abastecimiento/
Authorization: Bearer {{validador_abast_empresa_token}}
Content-Type: application/json

{
    "accion": "aprobar",
    "comentario": "Stock interno verificado. No tenemos estos equipos disponibles.",
    "stock_validado": true,
    "observaciones_tecnicas": "Especificaciones técnicas validadas"
}
```

**Tests:**
```javascript
pm.test("Abastecimiento validado correctamente", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.solicitud.estado).to.equal("pendiente_finanzas");
});
```

---

#### **Test 8.5: Listar Solicitudes Pendientes Finanzas**
```http
GET {{base_url}}/api/solicitudes/pendientes-finanzas/
Authorization: Bearer {{validador_fin_empresa_token}}
```

**Tests:**
```javascript
pm.test("Lista de solicitudes pendientes finanzas", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.results).to.be.an('array');
});
```

---

#### **Test 8.6: Validar Finanzas Empresa (HU13)**
```http
POST {{base_url}}/api/solicitudes/{{solicitud_id}}/validar-finanzas/
Authorization: Bearer {{validador_fin_empresa_token}}
Content-Type: application/json

{
    "accion": "aprobar",
    "comentario": "Presupuesto disponible. Proyecto aprobado por gerencia.",
    "presupuesto_aprobado": 25500000.00,
    "forma_pago_preferida": "credito",
    "observaciones_financieras": "Cliente con buen historial crediticio"
}
```

**Tests:**
```javascript
pm.test("Finanzas validadas correctamente", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.solicitud.estado).to.equal("aprobada");
});
```

---

### 📁 **COLECCIÓN 9: FLUJO LAMBDA - PEDIDOS (HU14-HU16)**

#### **Test 9.1: Convertir Solicitud a Pedido (HU14)**
```http
POST {{base_url}}/api/pedidos/convertir-solicitud/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "solicitud_id": "{{solicitud_id}}"
}
```

**Tests:**
```javascript
pm.test("Solicitud convertida a pedido", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response.pedido).to.have.property("id");
    pm.expect(response.pedido.estado).to.equal("pendiente_validacion_lambda");
    pm.environment.set("pedido_id", response.pedido.id);
});
```

---

#### **Test 9.2: Asignar Área Lambda**
```http
POST {{base_url}}/api/pedidos/{{pedido_id}}/asignar-area-lambda/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "area_destino": "abastecimiento",
    "observaciones": "Validar disponibilidad de productos especiales"
}
```

**Tests:**
```javascript
pm.test("Pedido asignado a área abastecimiento Lambda", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.pedido.estado).to.equal("pendiente_abastecimiento_lambda");
});
```

---

#### **Test 9.3: Crear Validadores Lambda**

**Crear Validador Abastecimiento Lambda:**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "email": "{{validador_abast_lambda_email}}",
    "nombres": "Ana",
    "apellidos": "Validadora Abastecimiento Lambda",
    "cargo": "Coordinadora de Inventario Lambda",
    "password": "{{validador_abast_lambda_password}}",
    "empresa": null,
    "area_lambda": "abastecimiento"
}
```

**Asignar Rol:**
```http
POST {{base_url}}/api/usuarios/{{validador_abast_lambda_id}}/asignar-rol/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "grupo": "Validador Abastecimiento Lambda"
}
```

**Asignar Permisos:**
```http
POST {{base_url}}/api/usuarios/{{validador_abast_lambda_id}}/permisos-especiales/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "permisos": {
        "validador_abastecimiento": true
    }
}
```

---

#### **Test 9.4: Login Validador Abastecimiento Lambda**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{validador_abast_lambda_email}}",
    "password": "{{validador_abast_lambda_password}}"
}
```

**Tests:**
```javascript
pm.test("Login Validador Abastecimiento Lambda exitoso", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.environment.set("validador_abast_lambda_token", response.access);
});
```

---

#### **Test 9.5: Validar Abastecimiento Lambda**
```http
POST {{base_url}}/api/pedidos/{{pedido_id}}/validar-abastecimiento/
Authorization: Bearer {{validador_abast_lambda_token}}
Content-Type: application/json

{
    "accion": "aprobar",
    "observaciones": "Stock confirmado. Laptops: 10 disponibles, Servidores: 5 disponibles",
    "modificaciones_stock": [
        {
            "producto_id": "{{producto_laptop_id}}",
            "cantidad_reservada": 3
        },
        {
            "producto_id": "{{producto_servidor_id}}",
            "cantidad_reservada": 1
        }
    ]
}
```

**Tests:**
```javascript
pm.test("Abastecimiento Lambda validado", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.pedido.estado).to.equal("pendiente_finanzas_lambda");
});
```

---

#### **Test 9.6: Crear y Configurar Validador Finanzas Lambda**

**Crear usuario:**
```http
POST {{base_url}}/api/usuarios/empleados/crear/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "email": "{{validador_fin_lambda_email}}",
    "nombres": "Luis",
    "apellidos": "Validador Finanzas Lambda",
    "cargo": "Coordinador Financiero Lambda",
    "password": "{{validador_fin_lambda_password}}",
    "empresa": null,
    "area_lambda": "finanzas"
}
```

**Login:**
```http
POST {{base_url}}/api/token/
Content-Type: application/json

{
    "email": "{{validador_fin_lambda_email}}",
    "password": "{{validador_fin_lambda_password}}"
}
```

---

#### **Test 9.7: Validar Finanzas Lambda (HU15)**
```http
POST {{base_url}}/api/pedidos/{{pedido_id}}/validar-finanzas/
Authorization: Bearer {{validador_fin_lambda_token}}
Content-Type: application/json

{
    "accion": "aprobar",
    "observaciones": "Cliente con buen historial crediticio. Aprobando crédito a 30 días.",
    "condiciones_pago": {
        "forma_pago": "credito",
        "dias_credito": 30,
        "descuento_pronto_pago": 2.5
    },
    "limite_credito_asignado": 30000000.00
}
```

**Tests:**
```javascript
pm.test("Finanzas Lambda validadas", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.pedido.estado).to.equal("pendiente_pago");
});
```

---

### 📁 **COLECCIÓN 10: GESTIÓN DE PAGOS (HU16)**

#### **Test 10.1: Cliente Confirma Pago**
```http
POST {{base_url}}/api/pedidos/{{pedido_id}}/gestionar-pago/
Authorization: Bearer {{admin_empresa_token}}
Content-Type: application/json

{
    "accion": "confirmar_pago",
    "metodo_pago": "transferencia_bancaria",
    "numero_transaccion": "TRF-789456123",
    "monto_pagado": 25500000.00,
    "fecha_pago": "2025-10-20",
    "observaciones": "Transferencia desde cuenta corriente Bancolombia"
}
```

**Tests:**
```javascript
pm.test("Pago confirmado correctamente", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.pedido.estado).to.equal("pago_confirmado");
});
```

---

#### **Test 10.2: Marcar como Facturado**
```http
POST {{base_url}}/api/pedidos/{{pedido_id}}/marcar-facturado/
Authorization: Bearer {{admin_lambda_token}}
Content-Type: application/json

{
    "numero_factura": "FACT-2025-1234",
    "fecha_facturacion": "2025-10-20",
    "valor_facturado": 25500000.00,
    "observaciones": "Factura generada según condiciones pactadas"
}
```

**Tests:**
```javascript
pm.test("Pedido facturado correctamente", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response.pedido.estado).to.equal("facturado");
});
```

---

### 📁 **COLECCIÓN 11: REPORTES Y DASHBOARD**

#### **Test 11.1: Dashboard Lambda**
```http
GET {{base_url}}/api/pedidos/dashboard/
Authorization: Bearer {{admin_lambda_token}}
```

**Tests:**
```javascript
pm.test("Dashboard Lambda funciona", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response).to.have.property("pedidos_pendientes_abastecimiento");
    pm.expect(response).to.have.property("pedidos_pendientes_finanzas");
});
```

---

#### **Test 11.2: Productos Bajo Mínimo**
```http
GET {{base_url}}/api/productos/bajo-minimo/
Authorization: Bearer {{admin_lambda_token}}
```

**Tests:**
```javascript
pm.test("Productos bajo mínimo", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response).to.be.an('array');
});
```

---

## 🎯 **ORDEN DE EJECUCIÓN DE PRUEBAS**

### **Fase 1: Configuración (Colecciones 1-2)**
1. Crear Admin Lambda
2. Login Admin Lambda  
3. Crear Empresa Cliente
4. Listar Empresas

### **Fase 2: Usuarios y Roles (Colecciones 3-6)**
5. Crear Admin Empresa
6. Crear Áreas
7. Crear todos los empleados
8. Asignar roles y permisos
9. Login de todos los usuarios

### **Fase 3: Productos (Colección 7)**
10. Crear catálogo de productos

### **Fase 4: Flujo Empresa Cliente (Colección 8)**
11. Crear solicitud
12. Flujo completo de validación empresa (4 pasos)

### **Fase 5: Flujo Lambda (Colecciones 9-10)**
13. Conversión a pedido
14. Flujo completo de validación Lambda (4 pasos)
15. Gestión de pagos

### **Fase 6: Verificación (Colección 11)**
16. Reportes y dashboards

---

## 📊 **RESULTADOS ESPERADOS**

Al final de todas las pruebas deberías tener:

- ✅ 1 Empresa cliente creada y activa
- ✅ 7 usuarios con diferentes roles funcionando
- ✅ 2 productos en catálogo
- ✅ 1 solicitud procesada completamente (8 pasos)
- ✅ 1 pedido facturado (estado final)
- ✅ Dashboard con estadísticas
- ✅ Sistema 100% funcional

**¡Esta suite de pruebas valida todo el sistema B2B de principio a fin!** 🚀