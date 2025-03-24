document.addEventListener('DOMContentLoaded', () => {
    // Fetch existing cart data and update cart count
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const cartCountElement = document.getElementById('cartCount');
    if (cartCountElement) {
        cartCountElement.innerText = cart.length; // Update count based on local storage
    }
});

// Redirect to the cart page
function redirectToCart() {
    window.location.href = './cart.html'; // Adjust the URL as needed
}