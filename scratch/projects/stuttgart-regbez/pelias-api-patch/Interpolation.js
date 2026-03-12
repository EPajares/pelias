const url = require('url');
const _ = require('lodash');
const Debug = require('../../helper/debug');
const debugLog = new Debug('interpolation:request');
const querystring = require('querystring');

const ServiceConfiguration = require('pelias-microservice-wrapper').ServiceConfiguration;

class Interpolation extends ServiceConfiguration {
  constructor(o) {
    super('interpolation', o);
  }

  getInterpolationNumber(req) {
    const parsedText = _.get(req, 'clean.parsed_text', {});
    const housenumber = parsedText.housenumber;
    const unit = parsedText.unit;
    const queryText = _.get(req, 'clean.query.text') || _.get(req, 'clean.text') || '';

    if (_.isString(housenumber) && _.isString(unit) && _.isString(queryText)) {
      const unitTrimmed = unit.trim();
      const housenumberTrimmed = housenumber.trim();

      if (!_.isEmpty(unitTrimmed) && !_.isEmpty(housenumberTrimmed)) {
        const slashPattern = new RegExp(
          `\\b${_.escapeRegExp(unitTrimmed)}\\s*\\/\\s*${_.escapeRegExp(housenumberTrimmed)}\\b`
        );

        if (slashPattern.test(queryText)) {
          return unitTrimmed;
        }
      }
    }

    return housenumber;
  }

  getStreetValue(req, hit) {
    const rawStreet = hit.address_parts.street || req.clean.parsed_text.street;

    if (_.isArray(rawStreet)) {
      return _.find(rawStreet, value => _.isString(value) && !_.isEmpty(value.trim()));
    }

    if (_.isString(rawStreet)) {
      return rawStreet;
    }

    return undefined;
  }

  getParameters(req, hit) {
    let params = {
      number: this.getInterpolationNumber(req),
      street: this.getStreetValue(req, hit),
      lat: hit.center_point.lat,
      lon: hit.center_point.lon
    };

    return params;
  }

  getUrl(_req) {
    return url.resolve(this.baseUrl, 'search/geojson');
  }

  getQueryDebug(req, hit) {
    const params = this.getParameters(req, hit);

    if (req.clean.exposeInternalDebugTools) {
      const table = url.resolve(this.baseUrl, 'extract/table') + '?' + querystring.stringify({ ...params, names: params.street });
      const raw = this.getUrl() + '?' + querystring.stringify(params);
      const demo = url.resolve(this.baseUrl, 'demo') + `/#16/${hit.center_point.lat}/${hit.center_point.lon}` +
        '?' + querystring.stringify({ name: params.street });
      return { links: { table, raw, demo }, params };
    } else {
      return { params };
    }
  }
}

module.exports = Interpolation;
