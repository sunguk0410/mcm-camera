package sunguk.arfitting;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/customer-sessions")
@RequiredArgsConstructor
public class CustomerSessionController {

    private final CustomerSessionService customerSessionService;

    @PostMapping
    public ResponseEntity<CustomerSessionResponse> create(
            @Valid @RequestBody CreateCustomerSessionRequest request
    ) {
        CustomerSessionResponse response =
                customerSessionService.createOrGet(request);

        return ResponseEntity.ok(response);
    }
}
