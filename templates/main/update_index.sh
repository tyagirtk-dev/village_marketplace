#!/bin/bash

# Target file
FILE="templates/main/index.html"

# Purana code hatane aur naya Carousel lagane ke liye
sed -i '/<div class="py-5 mb-5"/,/<\/div>/c\
<div id="heroCarousel" class="carousel slide mb-5" data-bs-ride="carousel" data-bs-interval="3000">\
    <div class="carousel-inner">\
        {% for i in range(1, 4) %}\
        <div class="carousel-item {% if i == 1 %}active{% endif %}">\
            <img src="{{ url_for(\x27static\x27, filename=\x27hero_slides/slide\x27 + i|string + \x27.png\x27) }}" \
                 class="d-block w-100" style="height: 400px; object-fit: cover;" alt="Banner {{ i }}">\
        </div>\
        {% endfor %}\
    </div>\
</div>' $FILE

echo "Index file updated successfully!"
