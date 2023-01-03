

'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    const v = 0;
    if (typeof v === 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  const newcatalog = {
    "%(sel)s of %(cnt)s selected": [
      "%(sel)s\uac1c\uac00 %(cnt)s\uac1c \uc911\uc5d0 \uc120\ud0dd\ub428."
    ],
    "6 a.m.": "\uc624\uc804 6\uc2dc",
    "6 p.m.": "\uc624\ud6c4 6\uc2dc",
    "April": "4\uc6d4",
    "August": "8\uc6d4",
    "Available %s": "\uc774\uc6a9 \uac00\ub2a5\ud55c %s",
    "Cancel": "\ucde8\uc18c",
    "Choose": "\uc120\ud0dd",
    "Choose a Date": "\uc2dc\uac04 \uc120\ud0dd",
    "Choose a Time": "\uc2dc\uac04 \uc120\ud0dd",
    "Choose a time": "\uc2dc\uac04 \uc120\ud0dd",
    "Choose all": "\ubaa8\ub450 \uc120\ud0dd",
    "Chosen %s": "\uc120\ud0dd\ub41c %s",
    "Click to choose all %s at once.": "\ud55c\ubc88\uc5d0 \ubaa8\ub4e0 %s \ub97c \uc120\ud0dd\ud558\ub824\uba74 \ud074\ub9ad\ud558\uc138\uc694.",
    "Click to remove all chosen %s at once.": "\ud55c\ubc88\uc5d0 \uc120\ud0dd\ub41c \ubaa8\ub4e0 %s \ub97c \uc81c\uac70\ud558\ub824\uba74 \ud074\ub9ad\ud558\uc138\uc694.",
    "December": "12\uc6d4",
    "February": "2\uc6d4",
    "Filter": "\ud544\ud130",
    "Hide": "\uac10\ucd94\uae30",
    "January": "1\uc6d4",
    "July": "7\uc6d4",
    "June": "6\uc6d4",
    "March": "3\uc6d4",
    "May": "5\uc6d4",
    "Midnight": "\uc790\uc815",
    "Noon": "\uc815\uc624",
    "Note: You are %s hour ahead of server time.": [
      "Note: \uc11c\ubc84 \uc2dc\uac04\ubcf4\ub2e4 %s \uc2dc\uac04 \ube60\ub985\ub2c8\ub2e4."
    ],
    "Note: You are %s hour behind server time.": [
      "Note: \uc11c\ubc84 \uc2dc\uac04\ubcf4\ub2e4 %s \uc2dc\uac04 \ub2a6\uc740 \uc2dc\uac04\uc785\ub2c8\ub2e4."
    ],
    "November": "11\uc6d4",
    "Now": "\ud604\uc7ac",
    "October": "10\uc6d4",
    "Remove": "\uc0ad\uc81c",
    "Remove all": "\ubaa8\ub450 \uc81c\uac70",
    "September": "9\uc6d4",
    "Show": "\ubcf4\uae30",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "\uc0ac\uc6a9 \uac00\ub2a5\ud55c %s \uc758 \ub9ac\uc2a4\ud2b8 \uc785\ub2c8\ub2e4.  \uc544\ub798\uc758 \uc0c1\uc790\uc5d0\uc11c \uc120\ud0dd\ud558\uace0 \ub450 \uc0c1\uc790 \uc0ac\uc774\uc758 \"\uc120\ud0dd\" \ud654\uc0b4\ud45c\ub97c \ud074\ub9ad\ud558\uc5ec \uba87 \uac00\uc9c0\ub97c \uc120\ud0dd\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "\uc120\ud0dd\ub41c %s \ub9ac\uc2a4\ud2b8 \uc785\ub2c8\ub2e4.  \uc544\ub798\uc758 \uc0c1\uc790\uc5d0\uc11c \uc120\ud0dd\ud558\uace0 \ub450 \uc0c1\uc790 \uc0ac\uc774\uc758 \"\uc81c\uac70\" \ud654\uc0b4\ud45c\ub97c \ud074\ub9ad\ud558\uc5ec \uc77c\ubd80\ub97c \uc81c\uac70 \ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
    "Today": "\uc624\ub298",
    "Tomorrow": "\ub0b4\uc77c",
    "Type into this box to filter down the list of available %s.": "\uc0ac\uc6a9 \uac00\ub2a5\ud55c %s \ub9ac\uc2a4\ud2b8\ub97c \ud544\ud130\ub9c1\ud558\ub824\uba74 \uc774 \uc0c1\uc790\uc5d0 \uc785\ub825\ud558\uc138\uc694.",
    "Yesterday": "\uc5b4\uc81c",
    "You have selected an action, and you haven\u2019t made any changes on individual fields. You\u2019re probably looking for the Go button rather than the Save button.": "\uac1c\ubcc4 \ud544\ub4dc\uc5d0 \uc544\ubb34\ub7f0 \ubcc0\uacbd\uc774 \uc5c6\ub294 \uc0c1\ud0dc\ub85c \uc561\uc158\uc744 \uc120\ud0dd\ud588\uc2b5\ub2c8\ub2e4. \uc800\uc7a5 \ubc84\ud2bc\uc774 \uc544\ub2c8\ub77c \uc9c4\ud589 \ubc84\ud2bc\uc744 \ucc3e\uc544\ubcf4\uc138\uc694.",
    "You have selected an action, but you haven\u2019t saved your changes to individual fields yet. Please click OK to save. You\u2019ll need to re-run the action.": "\uac1c\ubcc4 \ud544\ub4dc\uc758 \uac12\ub4e4\uc744 \uc800\uc7a5\ud558\uc9c0 \uc54a\uace0 \uc561\uc158\uc744 \uc120\ud0dd\ud588\uc2b5\ub2c8\ub2e4. OK\ub97c \ub204\ub974\uba74 \uc800\uc7a5\ub418\uba70, \uc561\uc158\uc744 \ud55c \ubc88 \ub354 \uc2e4\ud589\ud574\uc57c \ud569\ub2c8\ub2e4.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "\uac1c\ubcc4 \ud3b8\uc9d1 \uac00\ub2a5\ud55c \ud544\ub4dc\uc5d0 \uc800\uc7a5\ub418\uc9c0 \uc54a\uc740 \uac12\uc774 \uc788\uc2b5\ub2c8\ub2e4. \uc561\uc158\uc744 \uc218\ud589\ud558\uba74 \uc800\uc7a5\ub418\uc9c0 \uc54a\uc740 \uac12\ub4e4\uc744 \uc783\uc5b4\ubc84\ub9ac\uac8c \ub429\ub2c8\ub2e4.",
    "one letter Friday\u0004F": "\uae08",
    "one letter Monday\u0004M": "\uc6d4",
    "one letter Saturday\u0004S": "\ud1a0",
    "one letter Sunday\u0004S": "\uc77c",
    "one letter Thursday\u0004T": "\ubaa9",
    "one letter Tuesday\u0004T": "\ud654",
    "one letter Wednesday\u0004W": "\uc218"
  };
  for (const key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      const value = django.catalog[msgid];
      if (typeof value === 'undefined') {
        return msgid;
      } else {
        return (typeof value === 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      const value = django.catalog[singular];
      if (typeof value === 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value.constructor === Array ? value[django.pluralidx(count)] : value;
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      let value = django.gettext(context + '\x04' + msgid);
      if (value.includes('\x04')) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      let value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.includes('\x04')) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {
    "DATETIME_FORMAT": "Y\ub144 n\uc6d4 j\uc77c g:i A",
    "DATETIME_INPUT_FORMATS": [
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%m/%d/%Y %H:%M:%S",
      "%m/%d/%Y %H:%M:%S.%f",
      "%m/%d/%Y %H:%M",
      "%m/%d/%y %H:%M:%S",
      "%m/%d/%y %H:%M:%S.%f",
      "%m/%d/%y %H:%M",
      "%Y\ub144 %m\uc6d4 %d\uc77c %H\uc2dc %M\ubd84 %S\ucd08",
      "%Y\ub144 %m\uc6d4 %d\uc77c %H\uc2dc %M\ubd84",
      "%Y-%m-%d"
    ],
    "DATE_FORMAT": "Y\ub144 n\uc6d4 j\uc77c",
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d",
      "%m/%d/%Y",
      "%m/%d/%y",
      "%Y\ub144 %m\uc6d4 %d\uc77c"
    ],
    "DECIMAL_SEPARATOR": ".",
    "FIRST_DAY_OF_WEEK": 0,
    "MONTH_DAY_FORMAT": "n\uc6d4 j\uc77c",
    "NUMBER_GROUPING": 3,
    "SHORT_DATETIME_FORMAT": "Y-n-j H:i",
    "SHORT_DATE_FORMAT": "Y-n-j.",
    "THOUSAND_SEPARATOR": ",",
    "TIME_FORMAT": "A g:i",
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S",
      "%H:%M:%S.%f",
      "%H:%M",
      "%H\uc2dc %M\ubd84 %S\ucd08",
      "%H\uc2dc %M\ubd84"
    ],
    "YEAR_MONTH_FORMAT": "Y\ub144 n\uc6d4"
  };

    django.get_format = function(format_type) {
      const value = django.formats[format_type];
      if (typeof value === 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }
};

