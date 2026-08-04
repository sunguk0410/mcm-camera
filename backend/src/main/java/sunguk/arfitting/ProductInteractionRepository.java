package sunguk.arfitting;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ProductInteractionRepository extends JpaRepository<ProductInteraction, Long> {
    List<ProductInteraction>
    findAllByCustomerSessionIdOrderByOccurredAtDesc(Long customerSessionId);

}
