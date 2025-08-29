document.addEventListener("DOMContentLoaded", () => {
   // Loader animation
   const loaders = document.querySelectorAll(".loader");
   loaders.forEach(loader => {
       setTimeout(() => {
           loader.style.display = "none";
       }, 5000); // simule 5 sec max
   });
   // Boutons "Favoris"
   const favButtons = document.querySelectorAll(".fav-btn");
   favButtons.forEach(btn => {
       btn.addEventListener("click", () => {
           btn.classList.toggle("active");
           if (btn.classList.contains("active")) {
               btn.innerText = "★ Favori";
           } else {
               btn.innerText = "☆ Favori";
           }
       });
   });
});