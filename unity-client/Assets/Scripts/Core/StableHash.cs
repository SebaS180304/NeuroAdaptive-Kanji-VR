namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Hash de string a int, estable para siempre.
    ///
    /// POR QUE NO string.GetHashCode()
    /// -------------------------------
    /// Porque .NET no garantiza que devuelva el mismo valor entre ejecuciones
    /// del mismo programa, y de hecho en .NET Core lo aleatoriza por proceso
    /// como defensa contra ataques de colision de hash. Dos corridas de la
    /// misma sesion darian dos secuencias de trials distintas.
    ///
    /// Eso destruiria exactamente la propiedad por la que existe la seed: spec
    /// 6.1 pide que la seed y la secuencia permitan reconstruir la sesion de
    /// forma exacta. Y el fallo seria silencioso -- la sesion correria bien, con
    /// otros trials, y la diferencia solo aparecia al comparar dos analisis.
    ///
    /// FNV-1a de 32 bits es determinista por definicion: mismo texto, mismo
    /// numero, en cualquier maquina, en cualquier version del runtime y dentro
    /// de diez anos.
    /// </summary>
    public static class StableHash
    {
        private const uint FnvOffsetBasis = 2166136261;
        private const uint FnvPrime = 16777619;

        /// <summary>
        /// FNV-1a sobre los bytes UTF-16 del texto. Devuelve int porque es lo
        /// que consume System.Random; el unchecked es deliberado, el
        /// desbordamiento forma parte del algoritmo.
        /// </summary>
        public static int Of(string text)
        {
            if (string.IsNullOrEmpty(text)) return 0;

            unchecked
            {
                uint hash = FnvOffsetBasis;
                foreach (char c in text)
                {
                    hash ^= (byte)(c & 0xFF);
                    hash *= FnvPrime;
                    hash ^= (byte)(c >> 8);
                    hash *= FnvPrime;
                }
                return (int)hash;
            }
        }
    }
}
