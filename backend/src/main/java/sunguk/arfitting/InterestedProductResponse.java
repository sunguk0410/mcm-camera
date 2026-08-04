package sunguk.arfitting;

import java.time.LocalDateTime;

public record InterestedProductResponse(
        String productId,
        String productName,
        String imageUrl,
        String arAssetUrl,
        LocalDateTime lastInteractedAt
) {
}
