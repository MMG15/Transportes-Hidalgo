"""Errores del negocio. Las capas externas los traducen (p. ej. a códigos HTTP)."""


class ErrorDominio(Exception):
    """Base de todos los errores de negocio."""


class DatosInvalidos(ErrorDominio):
    """Un dato no cumple el formato o rango esperado."""


class NoEncontrado(ErrorDominio):
    """El recurso solicitado no existe."""


class Duplicado(ErrorDominio):
    """El recurso ya existe."""


class ReglaNegocioViolada(ErrorDominio):
    """La operación no está permitida por una regla del negocio."""


class NoAutenticado(ErrorDominio):
    """No hay un usuario identificado (o sus credenciales no son válidas)."""


class SinPermiso(ErrorDominio):
    """El usuario está identificado pero su rol no permite la operación."""
