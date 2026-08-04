package sunguk.arfitting;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ProductInteraction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    private CustomerSession customerSession;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    private Product product;

    @Enumerated(EnumType.STRING)
    private InteractionType interactionType;

    private LocalDateTime occurredAt;

    public ProductInteraction(
            CustomerSession customerSession,
            Product product,
            InteractionType interactionType
    ) {
        this.customerSession = customerSession;
        this.product = product;
        this.interactionType = interactionType;
        this.occurredAt = LocalDateTime.now();
    }
}