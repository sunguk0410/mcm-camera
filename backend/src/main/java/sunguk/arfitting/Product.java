package sunguk.arfitting;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Product {

    @Id
    private String id;

    private String name;

    private String imageUrl;

    private String arAssetUrl;

    public Product(
            String id,
            String name,
            String imageUrl,
            String arAssetUrl
    ) {
        this.id = id;
        this.name = name;
        this.imageUrl = imageUrl;
        this.arAssetUrl = arAssetUrl;
    }
}
