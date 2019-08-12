/* globals $ */
import 'jquery.cookie';

export class WelcomeMessage {  // eslint-disable-line import/prefer-default-export

  static dismissWelcomeMessage(dismissUrl) {
    $.ajax({
      type: 'POST',
      url: dismissUrl,
      headers: {
        'X-CSRFToken': $.cookie('csrftoken'),
      },
      success: () => {
        $('.welcome-message').hide();
      },
    });
  }

  constructor(options) {
    // Dismiss the welcome message if the user clicks dismiss, or auto-dismiss if
    // the user doesn't click dismiss in 7 days from when it was first viewed.

    // Check to see if the welcome message has been displayed at all.
    if ($('.welcome-message').length > 0) {
      // If the welcome message has been viewed.
      if ($.cookie('welcome-message-viewed') === 'True') {

        // If the welcome message is different from the previous one, update the cookies.
        if ($('.welcome-message')[0].id !== $.cookie('welcome-message-id')) {
          $.cookie('welcome-message-viewed', 'True', { expires: 365 });
          $.cookie('welcome-message-timer', 'True', { expires: 7 });
          $.cookie('welcome-message-id', $('.welcome-message')[0].id, { expires: 365 });
        }
        // If the timer cookie no longer exists, dismiss the welcome message.
        if ($.cookie('welcome-message-timer') !== 'True') {
          WelcomeMessage.dismissWelcomeMessage(options.dismissUrl);
          $.cookie('welcome-message-viewed', 'False', { expires: 365 });
        }

      } else {
        // Set the viewed cookie, the timer cookie and the id coookie.
        $.cookie('welcome-message-viewed', 'True', { expires: 365 });
        $.cookie('welcome-message-timer', 'True', { expires: 7 });
        $.cookie('welcome-message-id', $('.welcome-message')[0].id, { expires: 365 });
      }
    }
    $('.dismiss-message button').click(() => {
      WelcomeMessage.dismissWelcomeMessage(options.dismissUrl);
      // If the dissmiss button is clicked, set timer and viewed cookie to False.
      $.cookie('welcome-message-viewed', 'False', { expires: 365 });
      $.cookie('welcome-message-timer', 'False', { expires: 7 });
    });
  }
}
