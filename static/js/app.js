$('.ajax-post').on('submit', function(evt) {
  evt.preventDefault();
  $.ajax({
      type: 'POST',
      url: $(this).attr('action'),
      data: $(this).serialize(),
      success: function() { location.reload(); }
    });
});
