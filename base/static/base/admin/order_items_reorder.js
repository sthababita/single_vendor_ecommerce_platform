(function () {
    function init($) {
        if (!$) {
            return;
        }

        function moveOrderItemsBeforeShipment() {
            var $orderItemsInline = $('div.inline-group').filter(function () {
                var title = $(this).find('h2').first().text().trim();
                return title === 'Order items' || title.indexOf('Order items') !== -1;
            }).first();

            var $shipmentFieldset = $('fieldset').filter(function () {
                var title = $(this).find('h2').first().text().trim();
                return title === 'Shipment' || title.indexOf('Shipment') !== -1;
            }).first();

            if ($orderItemsInline.length && $shipmentFieldset.length) {
                $orderItemsInline.insertBefore($shipmentFieldset);
            }
        }

        function parseDecimal(value) {
            value = String(value).replace(/,/g, '').trim();
            return isNaN(value) || value === '' ? 0 : parseFloat(value);
        }

        function computeOrderItemSubtotal() {
            var subtotal = 0;

            $('.inline-related, .dynamic-orderitem_set').each(function () {
                var $row = $(this);
                var quantity = parseDecimal($row.find('input[name$="-quantity"]').val());
                var unitPrice = parseDecimal($row.find('input[name$="-unit_price"]').val());
                if (quantity > 0 && unitPrice > 0) {
                    subtotal += quantity * unitPrice;
                }
            });

            return subtotal;
        }

        function computeTotalAmount() {
            var subtotal = computeOrderItemSubtotal();
            var shipping = parseDecimal($('#id_shipping_amount').val());
            return subtotal + shipping;
        }

        function updateTotalAmountDisplay() {
            var total = computeTotalAmount();
            var formatted = total.toFixed(2);
            var $totalInput = $('#id_total_amount');
            var $totalReadonly = $('.field-total_amount .readonly, .field-total_amount p');

            if ($totalInput.length) {
                $totalInput.val(formatted);
            }
            if ($totalReadonly.length) {
                $totalReadonly.text(formatted);
            }
        }

        $(document).on('change', 'select[name$="-product"], input[name$="-quantity"], input[name$="-unit_price"], #id_shipping_amount', function () {
            updateTotalAmountDisplay();
        });

        $(document).ready(function () {
            moveOrderItemsBeforeShipment();
            updateTotalAmountDisplay();
        });
    }

    if (window.django && django.jQuery) {
        init(django.jQuery);
    } else {
        document.addEventListener('DOMContentLoaded', function () {
            init(window.django && django.jQuery);
        });
    }
})();
