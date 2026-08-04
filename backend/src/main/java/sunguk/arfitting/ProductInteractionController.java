package sunguk.arfitting;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/customer-sessions")
@RequiredArgsConstructor
public class ProductInteractionController {

    private final ProductInteractionService interactionService;

    @PostMapping("/{sessionId}/interactions")
    public ResponseEntity<Void> createInteraction(
            @PathVariable Long sessionId,
            @Valid @RequestBody CreateInteractionRequest request
    ) {
        interactionService.create(sessionId, request);

        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{sessionId}/interested-products")
    public List<InterestedProductResponse> findInterestedProducts(
            @PathVariable Long sessionId
    ) {
        return interactionService.findInterestedProducts(sessionId);
    }
}