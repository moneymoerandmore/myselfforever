# Avatar Runtime HTTP Client Sample

Copy `AvatarRuntimeHttpClient.h/.cpp` into an Unreal C++ module.

Your module `Build.cs` needs:

```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "Core",
    "CoreUObject",
    "Engine",
    "HTTP",
    "Json",
    "JsonUtilities"
});
```

Usage:

1. Add `UAvatarRuntimeHttpClient` to the avatar actor.
2. Set `BridgeBaseUrl` to `http://127.0.0.1:8820`.
3. Bind `OnAvatarState`.
4. Bind `OnAvatarSay`.
5. On `OnAvatarSay`, resolve relative `AudioUrl` against `BridgeBaseUrl`, play the audio, and feed the same stream/file into Audio2Face or your MetaHuman facial animation layer.

This sample deliberately stops at the runtime boundary. It does not generate
dialogue text and does not implement a 2D fallback.
