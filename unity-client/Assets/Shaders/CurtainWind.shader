// Curtain sheet of the pilot (D-F6-50, D-F6-53; Diseno_Sala_ESL.md §10.2, "Cortinas del piloto").
// Wind by vertex displacement: a slow wave that travels down the sheet, zero at the bar and growing to the
// hem, so it never pulls away from the bar and needs no collisions. Its clock is _WindTime, which
// EnvironmentMotion sets from the session seed and the time since activation (reconstructible like the sway).
// Transparent with the alpha of _BaseColor, fixed in the material: the wind moves vertices, never opacity.
// Lambert from the main light plus ambient, two-sided; no fresnel, specular or emission (rule 9).
Shader "NeuroAdaptive/CurtainWind"
{
    Properties
    {
        _BaseMap ("Base map", 2D) = "white" {}
        _BaseColor ("Base colour (alpha fixed at 0.90)", Color) = (1, 1, 1, 0.9)
        _WindAmplitude ("Amplitude at the hem (m)", Float) = 0.035
        _WindWaveLength ("Wave length down the sheet (m)", Float) = 0.9
        _WindPeriod ("Period (s)", Float) = 3.5
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
                float _WindWaveLength;
                float _WindPeriod;
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
                float hang = saturate((_TopY - p.y) / max(_Height, 1e-3));     // 0 at the bar, 1 at the hem
                float phase = TWO_PI * (_WindTime / max(_WindPeriod, 1e-3) - (_TopY - p.y) / max(_WindWaveLength, 1e-3));
                p += normalize(input.normalOS) * (_WindAmplitude * hang * hang * sin(phase));

                o.positionCS = TransformObjectToHClip(p);
                o.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                o.normalWS = TransformObjectToWorldNormal(input.normalOS);
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
