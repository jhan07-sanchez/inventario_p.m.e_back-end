from rest_framework.exceptions import APIException

from apps.core.exceptions.error_codes import ErrorCodes


class BusinessException(APIException):
    """
    Excepción base para reglas de negocio.
    """

    status_code = 400

    default_detail = "Ha ocurrido un error."

    default_code = ErrorCodes.VALIDATION_ERROR


class UserAlreadyExistsException(BusinessException):
    default_detail = "El usuario ya existe."

    default_code = ErrorCodes.USER_ALREADY_EXISTS


class EmailAlreadyExistsException(BusinessException):
    default_detail = "El correo electrónico ya existe."
    default_code = ErrorCodes.EMAIL_ALREADY_EXISTS


class DocumentAlreadyExistsException(BusinessException):
    default_detail = "El número de documento ya existe."
    default_code = ErrorCodes.DOCUMENT_ALREADY_EXISTS


class RoleAlreadyExistsException(BusinessException):
    default_detail = "El rol ya existe."
    default_code = ErrorCodes.ROLE_ALREADY_EXISTS


class UserInactiveException(BusinessException):
    default_detail = "El usuario se encuentra inactivo."
    default_code = ErrorCodes.USER_INACTIVE


class RoleInactiveException(BusinessException):
    default_detail = "El rol se encuentra inactivo."
    default_code = ErrorCodes.ROLE_INACTIVE


class NoActiveRoleException(BusinessException):
    """Se lanza cuando el usuario no tiene ningún rol activo."""

    default_detail = "El usuario no tiene ningún rol activo asignado."
    default_code = ErrorCodes.NO_ACTIVE_ROLE
    status_code = 403


class NoPermissionsException(BusinessException):
    """Se lanza cuando el usuario no posee permisos efectivos."""

    default_detail = "El usuario no posee permisos en el sistema."
    default_code = ErrorCodes.NO_PERMISSIONS
    status_code = 403


class UserRoleAlreadyExistsException(BusinessException):
    """
    Se lanza cuando un usuario ya tiene asignado
    el mismo rol.
    """

    default_detail = "El usuario ya tiene asignado este rol."
    default_code = ErrorCodes.USER_ROLE_ALREADY_EXISTS


class InvalidCredentialsException(BusinessException):
    default_detail = "Nombre de usuario o contraseña incorrectos."
    default_code = ErrorCodes.AUTHENTICATION_FAILED
    status_code = 401


class InvalidTokenException(BusinessException):
    default_detail = "El token es inválido o ha expirado."
    default_code = ErrorCodes.AUTHENTICATION_FAILED
    status_code = 401



class InvalidRolePermissionsException(BusinessException):
    """
    Se lanza cuando un rol contiene permisos
    que no están registrados en SecurityRegistry.
    """

    default_detail = (
        "El rol contiene permisos no registrados en el catálogo de seguridad."
    )
    default_code = ErrorCodes.INVALID_ROLE_PERMISSIONS



class CustomerAlreadyExistsException(BusinessException):
    default_detail = "El cliente ya existe."
    default_code = ErrorCodes.CUSTOMER_ALREADY_EXISTS

class CustomerInactiveException(BusinessException):
    default_detail = "El cliente se encuentra inactivo."
    default_code = ErrorCodes.CUSTOMER_INACTIVE



class SupplierAlreadyExistsException(BusinessException):
    """
    Se lanza cuando ya existe un proveedor
    con el mismo numero de documento.
    """
    default_detail = "El proveedor ya existe."
    default_code = ErrorCodes.SUPPLIER_ALREADY_EXISTS


class SupplierInactiveException(BusinessException):
    """
    Se lanza cuando el proveedor se encuentra inactivo.
    """
    default_detail = "El proveedor se encuentra inactivo."
    default_code = ErrorCodes.SUPPLIER_INACTIVE



class CategoryAlreadyExistsException(BusinessException):
    """
    Se lanza cuando ya existe una categoria
    """
    default_detail = "La categoria ya existe."
    default_code = ErrorCodes.CATEGORY_ALREADY_EXISTS


class CategoryInactiveException(BusinessException):
    """
    Se lanza cuando una categoria se encuentra inactiva
    """
    default_detail = "La categoria de encuentra Inactiva."
    default_code = ErrorCodes.CATEGORY_INACTIVE



class ProductAlreadyExistsException(BusinessException):
    """
    Se lanza cuando ya existe un producto
    con el mismo código interno o código de barras.
    """
    default_detail = "El producto ya existe."
    default_code = ErrorCodes.PRODUCT_ALREADY_EXISTS


class ProductInactiveException(BusinessException):
    """
    Se lanza cuando un producto se encuentra inactivo.
    """
    default_detail = "El producto se encuentra inactivo."
    default_code = ErrorCodes.PRODUCT_INACTIVE


class ProductCodeAlreadyExistsException(BusinessException):
    """
    Se lanza cuando ya existe un producto
    con el mismo código interno.
    """
    default_detail = "El código interno del producto ya existe."
    default_code = ErrorCodes.PRODUCT_CODE_ALREADY_EXISTS

class ProductBarcodeAlreadyExistsException(BusinessException):
    """
    Se lanza cuando ya existe un producto
    con el mismo código de barras.
    """
    default_detail = "El código de barras del producto ya existe."
    default_code = ErrorCodes.PRODUCT_BARCODE_ALREADY_EXISTS


class PurchaseNotFoundException(BusinessException):
    default_detail = "La compra especificada no existe."
    default_code = ErrorCodes.PURCHASE_NOT_FOUND
    status_code = 404


class InvalidPurchaseStateException(BusinessException):
    default_detail = "El estado actual de la compra no permite realizar esta operación."
    default_code = ErrorCodes.INVALID_PURCHASE_STATE


class InvalidPurchaseTransitionException(BusinessException):
    default_detail = "La transición de estado solicitada no es válida para esta compra."
    default_code = ErrorCodes.INVALID_PURCHASE_TRANSITION


class PurchaseHasNoDetailsException(BusinessException):
    default_detail = "La compra no tiene detalles asociados. No puede ser procesada."
    default_code = ErrorCodes.PURCHASE_HAS_NO_DETAILS


class InvoiceNotFoundException(BusinessException):
    default_detail = "La factura especificada no existe."
    default_code = ErrorCodes.INVOICE_NOT_FOUND
    status_code = 404


class InvalidInvoiceStateException(BusinessException):
    default_detail = "El estado actual de la factura no permite realizar esta operación."
    default_code = ErrorCodes.INVALID_INVOICE_STATE


class InvoiceTemplateNotFoundException(BusinessException):
    default_detail = "La plantilla de factura especificada no existe."
    default_code = ErrorCodes.INVOICE_TEMPLATE_NOT_FOUND
    status_code = 404


class InvoiceHasNoItemsException(BusinessException):
    default_detail = "La factura no tiene ítems asociados. No puede ser emitida."
    default_code = ErrorCodes.INVOICE_HAS_NO_ITEMS


class InvalidInvoiceTransitionException(BusinessException):
    default_detail = "La transición de estado solicitada no es válida para esta factura."
    default_code = ErrorCodes.INVALID_INVOICE_TRANSITION


class InvalidSaleStateException(BusinessException):
    default_detail = "El estado actual de la venta no permite realizar esta operacion."
    default_code = ErrorCodes.INVALID_SALE_STATE

class InvalidSaleTransitionException(BusinessException):
    default_detail = "La transacion de estado solicitada no es valida para esta venta."
    default_code = ErrorCodes.INVALID_SALE_TRANSITION

class SaleHasNoDetailsException(BusinessException):
    default_detail = "La venta no tiene detalles asociados. No puede ser procesada."
    default_code = ErrorCodes.SALE_HAS_NO_DETAILS
