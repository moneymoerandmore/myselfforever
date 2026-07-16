#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AvatarRuntimeHttpClient.generated.h"

USTRUCT(BlueprintType)
struct FAvatarRuntimeSayEvent
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    FString EventId;

    UPROPERTY(BlueprintReadOnly)
    FString Text;

    UPROPERTY(BlueprintReadOnly)
    FString AudioUrl;

    UPROPERTY(BlueprintReadOnly)
    FString AudioFormat;

    UPROPERTY(BlueprintReadOnly)
    FString VoiceProvider;

    UPROPERTY(BlueprintReadOnly)
    FString CharacterId;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FAvatarRuntimeStateDelegate, const FString&, EventId, const FString&, State);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FAvatarRuntimeSayDelegate, const FAvatarRuntimeSayEvent&, Event);

UCLASS(ClassGroup=(Avatar), meta=(BlueprintSpawnableComponent))
class UAvatarRuntimeHttpClient : public UActorComponent
{
    GENERATED_BODY()

public:
    UAvatarRuntimeHttpClient();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Avatar Runtime")
    FString BridgeBaseUrl = TEXT("http://127.0.0.1:8820");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Avatar Runtime")
    float PollTimeoutSeconds = 10.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Avatar Runtime")
    bool bAutoStart = true;

    UPROPERTY(BlueprintAssignable, Category="Avatar Runtime")
    FAvatarRuntimeStateDelegate OnAvatarState;

    UPROPERTY(BlueprintAssignable, Category="Avatar Runtime")
    FAvatarRuntimeSayDelegate OnAvatarSay;

    UFUNCTION(BlueprintCallable, Category="Avatar Runtime")
    void StartPolling();

    UFUNCTION(BlueprintCallable, Category="Avatar Runtime")
    void StopPolling();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    bool bPolling = false;
    bool bRequestInFlight = false;
    FString LastEventId;

    void PollOnce();
    void AckEvent(const FString& EventId, const FString& Status);
    FString AbsoluteBridgeUrl(const FString& Path) const;
};
