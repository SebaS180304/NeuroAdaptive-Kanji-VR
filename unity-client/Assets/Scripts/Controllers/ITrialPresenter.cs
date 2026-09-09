using System;
using System.Collections.Generic;
using NeuroAdaptiveVR.Data;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Lo que el sistema de respuesta necesita de la escena, y nada mas.
    ///
    /// Existe para que el ciclo del trial sea verificable sin escena. La
    /// escena `JapaneseLearningStudio` es trabajo del jueves; el ciclo y su
    /// telemetria se pueden probar hoy contra un presentador de consola, y
    /// eso significa que los eventos de trial llegan a la base esta misma
    /// tarde en vez de al final de la semana.
    ///
    /// Tambien delimita responsabilidades: el presentador dibuja y avisa de
    /// la eleccion; no valida, no mide tiempo y no emite telemetria. Si el
    /// presentador supiera si la respuesta fue correcta, habria dos sitios
    /// que deciden lo mismo.
    /// </summary>
    public interface ITrialPresenter
    {
        /// <summary>
        /// Muestra el prompt y las opciones. El sistema de respuesta arranca
        /// el cronometro **cuando este metodo vuelve**, no antes: el tiempo de
        /// presentacion no es tiempo de respuesta.
        /// </summary>
        void Present(RetrievalTrialType trialType, string promptText,
                     IReadOnlyList<TrialOption> options);

        /// <summary>Feedback tras la respuesta. `correctText` es el texto de la opcion correcta.</summary>
        void ShowFeedback(bool isCorrect, string correctText);

        /// <summary>Indica que hay ayuda disponible (o que no la hay) para este trial.</summary>
        void SetHintAvailable(bool available);

        /// <summary>Presenta el cue concedido por LAL.</summary>
        void ShowCue(LalCue cue);

        /// <summary>Limpia board y area de respuesta al cerrar el trial.</summary>
        void Clear();

        /// <summary>El participante eligio una opcion. Un paso: elegir es confirmar.</summary>
        event Action<string> OnOptionChosen;

        /// <summary>El participante pidio ayuda.</summary>
        event Action OnHintRequested;
    }
}
