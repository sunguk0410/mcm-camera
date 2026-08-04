package sunguk.arfitting;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Transactional
public class ProductInteractionService {

    private final CustomerSessionRepository customerSessionRepository;
    private final ProductRepository productRepository;
    private final ProductInteractionRepository interactionRepository;

    public void create(
            Long customerSessionId,
            CreateInteractionRequest request
    ) {
        CustomerSession session = customerSessionRepository
                .findById(customerSessionId)
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "Customer session not found"
                        )
                );

        Product product = productRepository
                .findById(request.productId())
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "Product not found"
                        )
                );

        ProductInteraction interaction =
                new ProductInteraction(
                        session,
                        product,
                        request.interactionType()
                );

        interactionRepository.save(interaction);
    }

    @Transactional(readOnly = true)
    public List<InterestedProductResponse> findInterestedProducts(
            Long customerSessionId
    ) {
        Map<String, InterestedProductResponse> products =
                new LinkedHashMap<>();

        interactionRepository
                .findAllByCustomerSessionIdOrderByOccurredAtDesc(
                        customerSessionId
                )
                .stream()
                .filter(interaction ->
                        interaction.getInteractionType()
                                == InteractionType.PICKED_UP
                )
                .forEach(interaction -> {
                    Product product = interaction.getProduct();

                    products.putIfAbsent(
                            product.getId(),
                            new InterestedProductResponse(
                                    product.getId(),
                                    product.getName(),
                                    product.getImageUrl(),
                                    product.getArAssetUrl(),
                                    interaction.getOccurredAt()
                            )
                    );
                });

        return new ArrayList<>(products.values());
    }
}