package sunguk.arfitting;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateInteractionRequest(
        @NotBlank String productId,
        @NotNull InteractionType interactionType
) {
}
