using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.Serialization;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Traduccion entre miembros de un enum de C# y los strings que viajan
    /// por el protocolo, tomando el valor de cable de
    /// <see cref="EnumMemberAttribute"/>.
    ///
    /// Existe porque el nombre del miembro y el valor de cable no coinciden y
    /// no deben coincidir: C# usa PascalCase, el backend y PostgreSQL usan
    /// SCREAMING_SNAKE_CASE. Serializar con .ToString() manda el nombre del
    /// miembro, que es el bug que se corrigio el 7 de septiembre de 2026 en
    /// GameFlowState (el payload es JSONB y aceptaba el string equivocado sin
    /// error, pero Pydantic lo rechaza con 422 y no castea al enum de la base).
    ///
    /// El atributo de cada miembro es la unica fuente de verdad: no hay una
    /// segunda lista que pueda desincronizarse.
    /// </summary>
    public static class EnumWire<T> where T : struct, Enum
    {
        private static readonly Dictionary<T, string> ToWire = BuildToWire();
        private static readonly Dictionary<string, T> FromWire = BuildFromWire();

        /// <summary>String que el backend espera para este valor.</summary>
        public static string Value(T member) => ToWire[member];

        /// <summary>
        /// Inverso de <see cref="Value"/>. Devuelve false si el string no
        /// corresponde a ningun miembro conocido, en vez de lanzar: un backend
        /// mas nuevo que este cliente no deberia tumbar la sesion.
        /// </summary>
        public static bool TryParse(string wireValue, out T member)
        {
            if (wireValue != null && FromWire.TryGetValue(wireValue, out member)) return true;
            member = default;
            return false;
        }

        private static Dictionary<T, string> BuildToWire()
        {
            var map = new Dictionary<T, string>();
            var type = typeof(T);

            foreach (T member in Enum.GetValues(type))
            {
                var field = type.GetField(member.ToString());
                var attribute = field?.GetCustomAttribute<EnumMemberAttribute>();

                // Fallo ruidoso y temprano, a proposito. Si el atributo falta
                // -- porque se agrego un miembro sin el, o porque el stripping
                // de IL2CPP lo elimino en un build -- queremos una excepcion en
                // el primer uso, no una sesion entera mandando en silencio
                // strings que el backend rechaza.
                if (attribute == null || string.IsNullOrEmpty(attribute.Value))
                {
                    throw new InvalidOperationException(
                        $"{type.Name}.{member} no tiene [EnumMember(Value = ...)]. " +
                        "Cada miembro necesita su valor de cable explicito para " +
                        "coincidir con el contrato del backend.");
                }

                map[member] = attribute.Value;
            }

            return map;
        }

        private static Dictionary<string, T> BuildFromWire()
        {
            var map = new Dictionary<string, T>();
            foreach (var pair in ToWire) map[pair.Value] = pair.Key;
            return map;
        }
    }
}
