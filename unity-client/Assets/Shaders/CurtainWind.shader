// Curtain sheet of the pilot (D-F6-50, D-F6-53; Diseno_Sala_ESL.md §10.2, "Cortinas del piloto").
// Wind by vertex displacement (D-F6-61, camino a): d = A · hang² · G(t) · R(x, t), along the
// sheet's normal towards the room only (d ≥ 0, so it never reaches the wall 15 cm behind), zero at the bar,
// at most A at the hem. G = (1 − g) + g sin(2π t / Tg) is a slow gust and R = (1 − r) + r sin(2π (x / λ − t / Tr))
// a ripple that travels across the sheet (g = r = 0.25: §10.2); the normals are
// recalculated from d, so the ripple reads as bands of light and shade moving slowly. Its clock is _WindTime,
// which EnvironmentMotion sets from the session seed and the time since activation (reconstructible).
// CurtainWind.Displacement in the editor is the same formula, sampled by the harness (X13).
// Transparent with the alpha of _BaseColor, fixed in the material: the wind moves vertices, never opacity.
// Lambert from the main light plus ambient, two-sided; no fresnel, specular or emission (rule 9).
Shader "NeuroAdaptive/CurtainWind"
{
    Properties
    {
        _BaseMap ("Base map", 2D) = "white" {}
        _BaseColor ("Base colour (alpha fixed at 0.90)", Color) = (1, 1, 1, 0.9)
        _WindAmplitude ("Peak displacement at the hem (m), at most 0.06", Float) = 0.06
        _GustPeriod ("Gust period (s)", Float) = 6
        _GustDepth ("Gust depth (±fraction)", Float) = 0.25
        _RippleDepth ("Ripple depth (±fraction)", Float) = 0.25
        _RippleWaveLength ("Ripple wave length across the sheet (m)", Float) = 0.45
        _RipplePeriod ("Ripple period (s)", Float) = 4
        _TopY ("Bar height, object space (m)", Float) = 0
        _Height ("Sheet height (m)", Float) = 1.3
        _WindTime ("Wind time (s), set by EnvironmentMotion", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                float _WindAmplitude;
                float _GustPeriod;
                float _GustDepth;
                float _RippleDepth;
                float _RippleWaveLength;
                float _RipplePeriod;
                float _TopY;
                float _Height;
                float _WindTime;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float3 p = input.positionOS.xyz;
                float3 n0 = normalize(input.normalOS);
                float height = max(_Height, 1e-3);
                float hang = saturate((_TopY - p.y) / height);                  // 0 at the bar, 1 at the hem
                float gust = 1.0 - _GustDepth + _GustDepth * sin(TWO_PI * _WindTime / max(_GustPeriod, 1e-3));
                // shortcut: the width runs along object x, as in the 16B sheets; a sheet across z needs p.z here
                float k = TWO_PI / max(_RippleWaveLength, 1e-3);
                float phase = k * p.x - TWO_PI * _WindTime / max(_RipplePeriod, 1e-3);
                float ripple = 1.0 - _RippleDepth + _RippleDepth * sin(phase);
                float scale = _WindAmplitude * gust;
                p += n0 * (scale * hang * hang * ripple);

                // Normal of the displaced sheet: n0 minus the gradient of d in the sheet's plane
                float dddx = scale * hang * hang * _RippleDepth * cos(phase) * k;
                float dddy = (_TopY - input.positionOS.y) < height ? -scale * ripple * 2.0 * hang / height : 0.0;
                float3 n = normalize(n0 - float3(dddx, dddy, 0.0));

                o.positionCS = TransformObjectToHClip(p);
                o.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                o.normalWS = TransformObjectToWorldNormal(n);
                o.fogFactor = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).rgb * _BaseColor.rgb;
                float3 n = normalize(input.normalWS);
                Light light = GetMainLight();
                half3 lit = light.color * abs(dot(n, light.direction)) + SampleSH(n);   // two-sided, independent of the view
                half3 colour = MixFog(albedo * lit, input.fogFactor);
                return half4(colour, _BaseColor.a);
            }
            ENDHLSL
        }
    }
}
