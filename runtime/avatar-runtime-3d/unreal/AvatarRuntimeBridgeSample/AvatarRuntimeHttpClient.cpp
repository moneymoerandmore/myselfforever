#include "AvatarRuntimeHttpClient.h"

#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "Json.h"
#include "JsonUtilities.h"

UAvatarRuntimeHttpClient::UAvatarRuntimeHttpClient()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UAvatarRuntimeHttpClient::BeginPlay()
{
    Super::BeginPlay();
    if (bAutoStart)
    {
        StartPolling();
    }
}

void UAvatarRuntimeHttpClient::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    StopPolling();
    Super::EndPlay(EndPlayReason);
}

void UAvatarRuntimeHttpClient::StartPolling()
{
    if (bPolling)
    {
        return;
    }
    bPolling = true;
    PollOnce();
}

void UAvatarRuntimeHttpClient::StopPolling()
{
    bPolling = false;
}

FString UAvatarRuntimeHttpClient::AbsoluteBridgeUrl(const FString& Path) const
{
    FString Base = BridgeBaseUrl;
    Base.RemoveFromEnd(TEXT("/"));
    return Base + Path;
}

void UAvatarRuntimeHttpClient::PollOnce()
{
    if (!bPolling || bRequestInFlight)
    {
        return;
    }

    bRequestInFlight = true;
    const FString Url = FString::Printf(
        TEXT("%s/api/unreal/events?after=%s&timeout=%.1f"),
        *BridgeBaseUrl,
        *FGenericPlatformHttp::UrlEncode(LastEventId),
        PollTimeoutSeconds
    );

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(Url);
    Request->SetVerb(TEXT("GET"));
    Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
    Request->OnProcessRequestComplete().BindLambda(
        [this](FHttpRequestPtr HttpRequest, FHttpResponsePtr Response, bool bSucceeded)
        {
            bRequestInFlight = false;
            if (bSucceeded && Response.IsValid() && Response->GetResponseCode() == 200)
            {
                TSharedPtr<FJsonObject> Root;
                const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
                if (FJsonSerializer::Deserialize(Reader, Root) && Root.IsValid())
                {
                    const TSharedPtr<FJsonObject>* Result = nullptr;
                    if (Root->TryGetObjectField(TEXT("result"), Result) && Result && Result->IsValid())
                    {
                        const TArray<TSharedPtr<FJsonValue>>* Events = nullptr;
                        if ((*Result)->TryGetArrayField(TEXT("events"), Events) && Events)
                        {
                            for (const TSharedPtr<FJsonValue>& Value : *Events)
                            {
                                const TSharedPtr<FJsonObject> Event = Value->AsObject();
                                if (!Event.IsValid())
                                {
                                    continue;
                                }
                                const FString EventId = Event->GetStringField(TEXT("event_id"));
                                const FString Type = Event->GetStringField(TEXT("type"));
                                const TSharedPtr<FJsonObject>* Payload = nullptr;
                                if (!Event->TryGetObjectField(TEXT("payload"), Payload) || !Payload || !Payload->IsValid())
                                {
                                    continue;
                                }

                                LastEventId = EventId;
                                if (Type == TEXT("state"))
                                {
                                    OnAvatarState.Broadcast(EventId, (*Payload)->GetStringField(TEXT("state")));
                                    AckEvent(EventId, TEXT("state_handled"));
                                }
                                else if (Type == TEXT("say"))
                                {
                                    FAvatarRuntimeSayEvent Say;
                                    Say.EventId = EventId;
                                    Say.Text = (*Payload)->GetStringField(TEXT("text"));
                                    Say.AudioUrl = (*Payload)->GetStringField(TEXT("audio_url"));
                                    Say.AudioFormat = (*Payload)->GetStringField(TEXT("audio_format"));
                                    Say.VoiceProvider = (*Payload)->GetStringField(TEXT("voice_provider"));
                                    Say.CharacterId = (*Payload)->GetStringField(TEXT("character_id"));
                                    OnAvatarSay.Broadcast(Say);
                                    AckEvent(EventId, TEXT("say_handled"));
                                }
                            }
                        }
                    }
                }
            }

            if (bPolling)
            {
                PollOnce();
            }
        }
    );
    Request->ProcessRequest();
}

void UAvatarRuntimeHttpClient::AckEvent(const FString& EventId, const FString& Status)
{
    if (EventId.IsEmpty())
    {
        return;
    }

    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(AbsoluteBridgeUrl(TEXT("/api/unreal/ack")));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));

    TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("event_id"), EventId);
    Body->SetStringField(TEXT("status"), Status);
    FString Serialized;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Serialized);
    FJsonSerializer::Serialize(Body, Writer);
    Request->SetContentAsString(Serialized);
    Request->ProcessRequest();
}
