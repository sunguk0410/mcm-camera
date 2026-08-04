package sunguk.arfitting;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateCustomerSessionRequest(
        @NotBlank String cameraId,
        @NotNull Long trackId
) {
}
